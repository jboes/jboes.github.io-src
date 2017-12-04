from ase.calculators.singlepoint import SinglePointCalculator as SPC
from ase.constraints import dict2constraint
from ase.io import read, write
from ase.units import Ry, Bohr
import msgpack
from ase import Atoms
from hpcio import get_nnodes
import numpy as np
import json
import os
# 1.889726 is the atomic unit of length per Angstrom (aul/A)
aul = 1.889726

try:
    from espresso import espresso
except:
    # Running off the server
    pass


def get_relaxed_calculation(in_file='output.traj'):
    """ Attach a stored calculator in the current directory
    to the provided atoms object.

    Then return the atoms object with the calculator attached.
    """

    # Read the last geometry from the input file
    atoms = read(in_file)

    # Reinitialize the calculator from calc.tgz and attach it.
    calc = espresso(**atoms.info)
    calc.load_flev_output()
    atoms.set_calculator(calc)

    return atoms


def get_potential_energy(in_file='input.traj'):
    """ Performs a ASE get_potential_energy() call with
    the ase-espresso calculator with the keywords
    defined inside the atoms object information.

    This can be a singlepoint calculation or a
    full relaxation depending on the keywords.
    """

    # Read the input file from the current directory
    atoms = read(in_file)

    # Planewave basis set requires periodic boundary conditions
    atoms.set_pbc([1, 1, 1])

    # Assign kpoints to be split across nodes
    if get_nnodes() > 1:
        if not sum(atoms.info['kpts']) == 1:
            atoms.info['parflags'] = '-npool {}'.format(get_nnodes())

    # Setting up the calculator
    calc = espresso(**atoms.info)
    atoms.set_calculator(calc)

    # Perform the calculation and write trajectory from log.
    atoms.get_potential_energy()
    images = log_to_atoms(out_file='output.traj')

    # Save the calculator to the local disk for later use.
    try:
        calc.save_flev_output()
    except(RuntimeError):
        calc.save_output()

    return atoms_to_encode(images)


def get_total_potential(out_file='potential.msg'):
    """ Calculate and save the total potential
    """

    # We require a previously relaxed calculation for this.
    atoms = get_relaxed_calculation()
    calc = atoms.get_calculator()

    # Collect the total potential and write to disk
    potential = calc.extract_total_potential()

    potential = list(potential)
    array_to_list(potential)

    # If outfile, write a MessagePack encoded version to disk
    if out_file:
        with open(out_file, 'w') as f:
            msgpack.dump(potential, f)

    # Return a BSON friendly version
    return json.dumps(potential, encoding='utf-8')


def array_to_list(data):
    """ A function to covert all arrays in a structure of
    embeded dictionaries and lists into lists themselves.
    """

    if isinstance(data, list):
        for i, v in enumerate(data):
            if isinstance(v, np.ndarray):
                data[i] = v.tolist()

            elif isinstance(v, dict):
                array_to_list(v)
            elif isinstance(v, list):
                array_to_list(v)

    elif isinstance(data, dict):
        for k, v in list(data.items()):
            if isinstance(v, np.ndarray):
                data[k] = v.tolist()

            elif isinstance(v, dict):
                array_to_list(v)
            elif isinstance(v, list):
                array_to_list(v)


def encode_to_atoms(encode, out_file='input.traj'):
    """ Dump the encoding to a local traj file.
    """

    # First, decode the trajectory
    data = json.loads(encode, encoding='utf-8')

    # Construct the initial atoms object
    atoms = Atoms(
        data['numbers'],
        data['trajectory']['0']['positions'],
        cell=data['trajectory']['0']['cell'],
        pbc=data['pbc'])
    atoms.info = data['calculator_parameters']
    atoms.set_constraint([dict2constraint(_) for _ in data['constraints']])

    # Attach the calculator
    calc = SPC(
        atoms=atoms,
        energy=data['trajectory']['0'].get('energy'),
        forces=data['trajectory']['0'].get('forces'),
        stress=data['trajectory']['0'].get('stress'))
    atoms.set_calculator(calc)

    # Collect the rest of the trajectory information
    images = [atoms]
    for i in range(len(data['trajectory']))[1:]:
        atoms = atoms.copy()

        if data['trajectory'][str(i)]['cell']:
            atoms.set_cell(data['trajectory'][str(i)]['cell'])

        if data['trajectory'][str(i)]['positions']:
            atoms.set_positions(data['trajectory'][str(i)]['positions'])

        calc = SPC(
            atoms=atoms,
            energy=data['trajectory'][str(i)].get('energy'),
            forces=data['trajectory'][str(i)].get('forces'),
            stress=data['trajectory'][str(i)].get('stress'))
        atoms.set_calculator(calc)

        images += [atoms]

    # Write the traj file
    if out_file:
        write(out_file, images)

    return images


def atoms_to_encode(images):
    """ Converts an list of atoms objects to an encoding
    from a .traj file.
    """

    if not isinstance(images, list):
        images = [images]

    # Convert all constraints into dictionary format
    constraints = [_.todict() for _ in images[0].constraints]
    for i, C in enumerate(constraints):

        # Turn any arrays in the kwargs into lists
        for k, v in list(C['kwargs'].items()):
            if isinstance(v, np.ndarray):
                constraints[i]['kwargs'][k] = v.tolist()

    # Convert any arrays from the parameter settings into lists
    keys = images[0].info
    for k, v in list(keys.items()):
        if isinstance(v, np.ndarray):
            keys[k] = v.tolist()

    data = {'trajectory': {}}
    # Assemble the compressed dictionary of results
    for i, atoms in enumerate(images):

        if i == 0:
            # For first images, collect cell and positions normally
            pos = atoms.get_positions()
            update_pos = pos

            cell = atoms.get_cell()
            update_cell = cell

            # Add the parameters which do not change
            data['numbers'] = images[0].get_atomic_numbers().tolist()
            data['pbc'] = images[0].get_pbc().tolist()
            data['constraints'] = constraints
            data['calculator_parameters'] = keys

        else:
            # For consecutive images, check for duplication
            # If duplicates are found, do not store it
            if np.array_equal(atoms.get_positions(), pos):
                update_pos = np.array([])
            else:
                pos = atoms.get_positions()
                update_pos = pos

            if np.array_equal(atoms.get_cell(), cell):
                update_cell = np.array([])
            else:
                cell = atoms.get_cell()
                update_cell = cell

        if atoms._calc:
            nrg = atoms.get_potential_energy()
            force = atoms.get_forces()
            stress = atoms.get_stress()

            # Stage results and convert to lists in needed
            results = {
                'positions': update_pos,
                'cell': update_cell,
                'energy': nrg,
                'forces': force,
                'stress': stress}

        else:
            results = {
                'positions': update_pos,
                'cell': update_cell}

        for k, v in list(results.items()):
            if isinstance(v, np.ndarray):
                results[k] = v.tolist()

        # Store trajectory, throwing out None values
        data['trajectory'][i] = {
            k: v for k, v in list(
                results.items()) if v is not None}

    # Return the reduced results in JSON compression
    return json.dumps(data)


def attach_results(f, atoms, write_file=True):
    """ Return the TS corrected energy for a scf instance
    in a log file and attach them to the given atoms obejct.

    Will also attach the forces and stress if applicable.
    """
    energy, forces, stress = None, None, None

    line = f.readline()
    while '!    total energy' not in line:
        line = f.readline()

    energy = float(line.split()[-2]) * Ry

    # Correct for non-zero temperature smearing
    for i in range(20):

        line = f.readline()
        if '     smearing contrib.' in line:
            energy -= 0.5 * float(line.split()[-2]) * Ry

        # Collect the forces on the atoms
        if 'Forces acting on atoms (Ry/au):' in line:
            for _ in range(4):
                line = f.readline()
                if 'atom' in line:
                    break

            forces = []
            for _ in range(len(atoms)):
                forces += [line.split()[-3:]]
                line = f.readline()

            forces = np.array(forces, dtype=float) / Ry * aul

            # If forces were located, attempt to find stress
            for i in range(10):
                line = f.readline()

                if 'total   stress' in line:

                    stress = []
                    for _ in range(3):
                        line = f.readline()
                        stress += [line.split()[-3:]]

                    stress = np.array(stress, dtype=float) / Ry * Bohr ** 3
                    break

    # attach the calculator
    calc = SPC(atoms=atoms,
               energy=energy,
               forces=forces,
               stress=stress)
    atoms.set_calculator(calc)

    return atoms


def log_to_atoms(log_file='log', ent=-1, out_file=None):
    """ Parse a QE log file for atoms trajectory and return a list
    of atoms objects representative of the relaxation path.

    NOTE: trajectory information is only returned for calculations
    run with BFGS internal to QE.
    """

    images = []
    with open(log_file) as f:
        line = f.readline()

        # Flag to read trajectory 'ent' only
        with os.popen(
                'grep -n Giannozzi ' +
                log_file +
                ' 2>/dev/null', 'r') as p:
            n = int(p.readlines()[ent].split()[0].strip(':'))

        for i in range(n):
            line = f.readline()

        # Read lines one at a time
        while line:
            line = f.readline()

            # Signifies a new trajectory
            # Clear any existing values from previous runs
            if '(npk)' in line:

                # Look for an input trajectory in the same file and use it
                # Convenient for conserving constraints, tags, and atoms info
                in_file = os.path.join(
                    '/'.join(log_file.split('/')[:-1]),
                    'input.traj')

                if os.path.exists(in_file):

                    # If it does exist, read it in as the initial configuration
                    atoms = read(in_file)
                    atoms.wrap()
                    natoms = len(atoms)
                    pos = atoms.get_positions()

                    # Skip past the geometry information
                    while 'site n.' not in line:
                        line = f.readline()

                # Otherwise, collect from the data
                else:
                    atoms = None

            # Example properties
            ######################
            # bravais-lattice index     =            0
            # lattice parameter (alat)  =       1.8897  a.u.
            # unit-cell volume          =    3209.1777 (a.u.)^3
            # number of atoms/cell      =            5
            # number of atomic types    =            2
            # number of electrons       =        45.00
            # number of Kohn-Sham states=           55
            # kinetic-energy cutoff     =      36.7493  Ry
            # charge density cutoff     =     367.4932  Ry
            # convergence threshold     =      7.3E-08
            # mixing beta               =       0.1000
            # number of iterations used =            8  plain     mixing
            # Exchange-correlation      = BEEF ( 1  4 27 13 2)
            # nstep                     =           50

            # Collect potentially relevent properties
            # The elif can be omitted if order is assured
            elif 'number of atoms/cell      =' in line:
                natoms = int(line.split()[-1])

            # Collect cell dimensions
            elif 'celldm(1)' in line:
                alat = float(line.split()[1]) / aul

            elif 'crystal' in line:
                cell = []
                for _ in range(3):
                    line = f.readline()
                    cell += [[float(x) for x in line.split()[3:6]]]
                cell = np.array(cell) * alat

            # Collect positions, symbols, and number of atoms
            elif 'site n.' in line:
                pos, syms = [], []

                for _ in range(natoms):
                    line = f.readline()
                    pos += [line.split()[-4:-1]]
                    syms += [line.split()[1].strip('0123456789')]

                pos = np.array(pos, dtype=float) * alat

                # Setup the atoms object
                atoms = Atoms(syms, pos, cell=cell, pbc=(1, 1, 1))

            # This should be the last piece of information
            elif 'number of k points=' in line:

                atoms = attach_results(f, atoms)

                # Add atom to images
                images = [atoms]

                # Only atomic positions and energies need to be collected now
                # until the calculation ends
                while 'JOB DONE.' not in line and line:
                    line = f.readline()

                    # A duplicate of the coordinates printed previously
                    if 'Begin final coordinates' in line:
                        break

                    if 'ATOMIC_POSITIONS' in line:
                        atoms = atoms.copy()

                        coord = line.split('(')[-1]
                        for i in range(natoms):
                            line = f.readline()
                            pos[i][:] = line.split()[1:4]

                            # It's possible to recover constraints here,
                            # but not yet implemented If there are 7
                            # characters in the line, we have constraints
                            # if len(line.split()) == 7:
                            #     cons += [line.split()[-3:]]
                            # else:
                            #     cons += [[1] * 3]

                        # cons = np.array(cons, dtype=float)

                        if coord == 'alat)':
                            atoms.set_positions(pos * alat)
                        elif coord == 'bohr)':
                            atoms.set_positions(pos * Bohr)
                        elif coord == 'angstrom)':
                            atoms.set_positions(pos)
                        else:
                            atoms.set_scaled_positions(pos)

                        # atoms.wrap()
                        atoms = attach_results(f, atoms)
                        images += [atoms]

                if out_file:
                    write(out_file, images)

                return images
