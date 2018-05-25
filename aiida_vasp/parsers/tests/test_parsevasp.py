"""Unittests for ParseVasp."""
# pylint:
# disable=unused-import,redefined-outer-name,unused-argument,unused-wildcard-import,wildcard-import

import numpy as np
import os
import pytest

from aiida.common.exceptions import ParsingError
from aiida_vasp.parsers.vasp import VaspParser
from aiida_vasp.utils.fixtures.testdata import data_path
from aiida_vasp.utils.fixtures import *


def xml_path(folder):
    """Set the path to the XML file."""
    return data_path(folder, 'vasprun.xml')


def xml_truncate(index, original, tmp):
    """Truncate vasprun.xml at the given line number and parse."""
    with open(original, 'r') as xmlfile:
        content = xmlfile.read().splitlines()
        truncated_content = '\n'.join(content[:-index or None])
    with open(tmp, 'w') as xmlfile:
        xmlfile.write(str(truncated_content))


@pytest.fixture(params=[0, 1])
def parse_result(request, aiida_env, tmpdir):
    """
    Give the result of parsing a retrieved calculation (emulated).

    Returns a function which does:

    1. create a calculation with parser settings
    2. update the parser settings with the extra_settings
    3. create a parser with the calculation
    4. populate a fake retrieved folder and pass it to the parser
    5. return the result
    """

    def parse(**extra_settings):
        """Run the parser using default settings updated with extra_settings."""
        from aiida.orm import CalculationFactory, DataFactory
        calc = CalculationFactory('vasp.vasp')()
        settings_dict = {'parser_settings': {'parse_potcar_file': False,
                                             'exception_on_bad_xml': False,
                                             'should_parse_OUTCAR': False,
                                             'should_parse_CONTCAR': False}}
        settings_dict.update(extra_settings)
        calc.use_settings(DataFactory('parameter')(dict=settings_dict))
        parser = VaspParser(calc=calc)
        retrieved = DataFactory('folder')()
        fldr = "basic"
        if "folder" in extra_settings:
            fldr = extra_settings["folder"]
        xml_file_path = xml_path(fldr)
        tmp_file_path = str(tmpdir.join('vasprun.xml'))
        #tmp_file_path = os.path.realpath(os.path.join(
        #    __file__, '../../../test_data/tmp/vasprun.xml'))
        xml_truncate(request.param, xml_file_path, tmp_file_path)
        retrieved.add_path(tmp_file_path, '')
        success, nodes = parser.parse_with_retrieved({'retrieved': retrieved})
        nodes = dict(nodes)
        return success, nodes

    return parse


def test_kpoints_result(parse_result):
    """Test that the kpoints result node is a KpointsData instance."""
    from aiida.orm import DataFactory
    _, nodes = parse_result(folder="basic")
    kpoints = nodes['output_kpoints']
    assert isinstance(kpoints, DataFactory('array.kpoints'))
    assert np.all(kpoints.get_kpoints()[0] ==
                  np.array([0.0, 0.0, 0.0]))
    assert np.all(kpoints.get_kpoints()[-1] ==
                  np.array([0.42857143, -0.42857143, 0.42857143]))


def test_kpoints_result(parse_result):
    """Test that the kpoints result node is a KpointsData instance."""
    from aiida.orm import DataFactory
    _, nodes = parse_result(folder="basic")
    kpoints = nodes['output_kpoints']
    assert isinstance(kpoints, DataFactory('array.kpoints'))
    assert np.all(kpoints.get_kpoints()[0] ==
                  np.array([0.0, 0.0, 0.0]))
    assert np.all(kpoints.get_kpoints()[-1] ==
                  np.array([0.42857143, -0.42857143, 0.42857143]))


def test_structure_result(parse_result):
    """Test that the structure result node is a StructureData instance,
    also check various other important properties.

    """
    from aiida.orm import DataFactory
    _, nodes = parse_result(folder="basic")
    structure = nodes['output_structure']
    # check object
    assert isinstance(structure, DataFactory('structure'))
    # check cell
    unitcell = structure.cell
    assert np.all(unitcell[0] == np.array([5.46503124, 0.0, 0.0]))
    assert np.all(unitcell[1] == np.array([0.0, 5.46503124, 0.0]))
    assert np.all(unitcell[2] == np.array([0.0, 0.0, 5.46503124]))
    # check first and last position
    assert np.all(structure.sites[0].position == np.array([0.0, 0.0, 0.0]))
    assert np.all(structure.sites[7].position == np.array([4.09877343,
                                                           4.09877343,
                                                           1.36625781]))
    # check volume
    assert structure.get_cell_volume() == np.float(163.22171870360754)


def test_forces_result(parse_result):
    """Check that the parsed forces are of type ArrayData and
    that the entries are as expected, e.g. correct value and
    that the first and last entry is the same (static run). """
    from aiida.orm import DataFactory
    _, nodes = parse_result(folder="basic")
    out_arr = nodes['output_trajectory_arr']
    out_traj = nodes['output_trajectory']
    # test object
    assert isinstance(out_arr, DataFactory('array'))
    out_arr = out_arr.get_array('forces')
    # test entries
    assert np.all(out_arr[0][0] == np.array([-0.24286901, 0.0, 0.0]))
    assert np.all(out_arr[0][-1] == np.array([-0.73887169,
                                              -0.43727184, -0.43727184]))
    # test object
    assert isinstance(out_traj, DataFactory('array.trajectory'))
    out_traj = out_traj.get_array('forces')
    # test entries
    assert np.all(out_traj[0][0] == np.array([-0.24286901, 0.0, 0.0]))
    assert np.all(out_traj[0][-1] == np.array([-0.73887169,
                                               -0.43727184, -0.43727184]))
    assert np.all(out_traj[0][-1] == out_traj[1][-1])
    assert np.all(out_traj[0][0] == out_traj[1][0])


def test_forces_result_relax(parse_result):
    """Check that the parsed forces are of type ArrayData and
    that the entries are as expected, e.g. correct value and
    that the first and last entry is the same (static run). """
    from aiida.orm import DataFactory
    _, nodes = parse_result(folder="relax")
    out = nodes['output_trajectory_arr']
    # test object
    assert isinstance(out, DataFactory('array'))
    out = out.get_array('forces')
    # test shape of array
    assert out.shape == (19, 8, 3)
    # test a few entries (first and last atom)
    assert np.all(out[0][0] == np.array([-2.42632080e-01,
                                         0.0,
                                         0.0]))
    assert np.all(out[0][-1] == np.array([-7.38879520e-01,
                                          -4.37063010e-01,
                                          -4.37063010e-01]))
    assert np.all(out[-1][0] == np.array([1.55852000e-03,
                                          0.0,
                                          0.0]))
    assert np.all(out[-1][-1] == np.array([-1.75970000e-03,
                                           1.12150000e-04,
                                           1.12150000e-04]))


def test_unitcells_result_relax(parse_result):
    """Check that the parsed unitcells are of type ArrayData and
    that the entries are as expected, e.g. correct value and
    that the first and last entry is the same (static run). """
    from aiida.orm import DataFactory
    _, nodes = parse_result(folder="relax")
    out = nodes['output_trajectory_arr']
    # test object
    assert isinstance(out, DataFactory('array'))
    out = out.get_array('cells')
    # test shape of array
    assert out.shape == (19, 3, 3)
    # test a few entries (first and last vector)
    assert np.all(out[0][0] == np.array([5.46503124e+00,
                                         0.0,
                                         0.0]))
    assert np.all(out[0][-1] == np.array([0.0,
                                          0.0,
                                          5.46503124e+00]))
    assert np.all(out[-1][0] == np.array([5.46702248e+00,
                                          0.0,
                                          0.0]))
    assert np.all(out[-1][-1] == np.array([0.0,
                                           2.19104000e-03,
                                           5.46705225e+00]))


def test_positions_result_relax(parse_result):
    """Check that the parsed positions are of type ArrayData and
    that the entries are as expected, e.g. correct value and
    that the first and last entry is the same (static run). """
    from aiida.orm import DataFactory
    _, nodes = parse_result(folder="relax")
    out = nodes['output_trajectory_arr']
    # test object
    assert isinstance(out, DataFactory('array'))
    out = out.get_array('positions')
    # test shape of array
    assert out.shape == (19, 8, 3)
    # test a few entries (first and last atom)
    assert np.all(out[0][0] == np.array([0.0,
                                         0.0,
                                         0.0]))
    assert np.all(out[0][-1] == np.array([0.75,
                                          0.75,
                                          0.25]))
    assert np.all(out[-1][0] == np.array([-0.00621692,
                                          0.0,
                                          0.0]))
    assert np.all(out[-1][-1] == np.array([0.7437189,
                                           0.74989833,
                                           0.24989833]))


def test_dielectrics_result(parse_result):
    """Check that the parsed positions are of type ArrayData and
    that the entries are as expected.

    """

    from aiida.orm import DataFactory
    _, nodes = parse_result(folder="dielectric")
    out = nodes['output_dielectrics']
    # test object
    assert isinstance(out, DataFactory('array'))
    imag = out.get_array('idiel')
    real = out.get_array('rdiel')
    energy = out.get_array('ediel')
    # test shape of array
    assert imag.shape == (1000, 6)
    assert real.shape == (1000, 6)
    assert energy.shape == (1000,)
    # test a few entries
    assert np.all(imag[0] == np.array([0.0,
                                       0.0,
                                       0.0,
                                       0.0,
                                       0.0,
                                       0.0]))
    assert np.all(imag[500] == np.array([0.0933,
                                         0.0924,
                                         0.0924,
                                         0.0,
                                         0.0082,
                                         0.0]))

    assert np.all(imag[999] == np.array([0.0035,
                                         0.0035,
                                         0.0035,
                                         0.0,
                                         0.0,
                                         0.0]))
    assert np.all(real[0] == np.array([12.0757,
                                       11.4969,
                                       11.4969,
                                       0.0,
                                       0.6477,
                                       0.0]))
    assert np.all(real[500] == np.array([-0.5237,
                                         -0.5366,
                                         -0.5366,
                                         0.0,
                                         0.0134,
                                         0.0]))
    assert np.all(real[999] == np.array([6.57100000e-01,
                                         6.55100000e-01,
                                         6.55100000e-01,
                                         0.0,
                                         -1.00000000e-04,
                                         0.0]))
    assert energy[500] == 10.2933


def test_born_result(parse_result):
    """Check that the Born effective charges are of type
    ArrayData and that the entries are as expected.

    """

    from aiida.orm import DataFactory
    _, nodes = parse_result(folder="localfield")
    out = nodes['output_born_charges']
    # test object
    assert isinstance(out, DataFactory('array'))
    born = out.get_array('born_charges')
    # test shape of array
    assert born.shape == (8, 3, 3)
    # test a few entries
    assert np.all(born[0][0] == np.array([6.37225000e-03,
                                          0.0,
                                          0.0]))
    assert np.all(born[0][-1] == np.array([-4.21760000e-04,
                                           -2.19570210e-01,
                                           3.20709600e-02]))
    assert np.all(born[4][0] == np.array([1.68565200e-01,
                                          -2.92058000e-02,
                                          -2.92058000e-02]))


def test_dos_result(parse_result):
    """Check that the density of states are of type ArrayData and
    that the entries are as expected.

    """

    from aiida.orm import DataFactory
    _, nodes = parse_result(folder="basic")
    out = nodes['output_dos']
    # test object
    assert isinstance(out, DataFactory('array'))
    dos = out.get_array('tdos')
    energy = out.get_array('edos')
    # test shape of array
    assert dos.shape == (301,)
    assert energy.shape == (301,)
    # test a few entries
    assert dos[150] == 4.1296
    assert energy[150] == 2.3373


def test_dos_spin_result(parse_result):
    """Check that the density of states are of type ArrayData and
    that the entries are as expected. This test is for spin
    separated systems.

    """

    from aiida.orm import DataFactory
    _, nodes = parse_result(folder="spin")
    out = nodes['output_dos']
    # test object
    assert isinstance(out, DataFactory('array'))
    dos = out.get_array('tdos')
    # test shape of array
    assert dos.shape == (2, 1000,)
    # test a few entries
    assert dos[0, 500] == 0.9839
    assert dos[1, 500] == 0.9844


def test_pdos_result(parse_result):
    """Check that the density of states are of type ArrayData and
    that the entries are as expected.

    """

    from aiida.orm import DataFactory
    _, nodes = parse_result(folder="partial")
    out = nodes['output_dos']
    # test object
    assert isinstance(out, DataFactory('array'))
    dos = out.get_array('pdos')
    energy = out.get_array('edos')
    # test shape of array
    assert dos.shape == (8, 1000, 9)
    assert energy.shape == (1000,)
    # test a few entries
    assert np.all(dos[3, 500] == np.array([0.0770, 0.0146, 0.0109,
                                           0.0155, 0.0, 0.0,
                                           0.0, 0.0, 0.0]))
    assert np.all(dos[7, 500] == np.array([0.0747, 0.0121, 0.0092,
                                           0.0116, 0.0, 0.0,
                                           0.0, 0.0, 0.0]))
    assert energy[500] == 0.01


def test_projectors_result(parse_result):
    """Check that the projectors are of type ArrayData and
    that the entries are as expected.

    """

    from aiida.orm import DataFactory
    _, nodes = parse_result(folder="partial")
    out = nodes['output_projectors']
    # test object
    assert isinstance(out, DataFactory('array'))
    proj = out.get_array('projectors')
    # test shape of array
    assert proj.shape == (8, 64, 21, 9)
    # test a few entries
    assert np.all(proj[0, 0, 5] == np.array([0.0,
                                             0.012,
                                             0.0123,
                                             0.0,
                                             0.0,
                                             0.0,
                                             0.0,
                                             0.0,
                                             0.0]))
    assert np.all(proj[7, 0, 5] == np.array([0.1909,
                                             0.0001,
                                             0.0001,
                                             0.0001,
                                             0.0,
                                             0.0,
                                             0.0,
                                             0.0,
                                             0.0]))
    assert np.all(proj[4, 3, 5] == np.array([0.2033,
                                             0.0001,
                                             0.0001,
                                             0.0001,
                                             0.0,
                                             0.0,
                                             0.0,
                                             0.0,
                                             0.0]))


def test_eigenocc_result(parse_result):
    """Check that the eigenvalues are of type BandData and
    that the entries are as expected. Also check the
    occupancies.

    """

    from aiida.orm import DataFactory
    _, nodes = parse_result(folder="basic")
    out = nodes['output_bands']
    # test object
    assert isinstance(out, DataFactory('array.bands'))
    eigenocc = out.get_bands(also_occupations=True)
    eigen = eigenocc[0]
    occ = eigenocc[1]
    # test shape of array
    assert eigen.shape == (64, 21)
    assert occ.shape == (64, 21)
    # test a few entries
    assert eigen[0, 0] == -6.2348
    assert eigen[0, 15] == 5.8956
    assert eigen[6, 4] == -1.7424
    assert occ[0, 0] == 1.0
    assert occ[0, 15] == 0.6949
    assert occ[6, 4] == 1.0


def test_eigenocc_spin_result(parse_result):
    """Check that the eigenvalues are of type BandData and
    that the entries are as expected. Also check the
    occupancies. This test is for spin separated systems.

    """

    from aiida.orm import DataFactory
    _, nodes = parse_result(folder="spin")
    out = nodes['output_bands']
    # test object
    assert isinstance(out, DataFactory('array.bands'))
    eigenocc = out.get_bands(also_occupations=True)
    eigen = eigenocc[0]
    occ = eigenocc[1]
    # test shape of array
    assert eigen.shape == (2, 64, 25)
    assert occ.shape == (2, 64, 25)
    # test a few entries
    assert eigen[0, 0, 0] == -6.2363
    assert eigen[0, 0, 15] == 5.8939
    assert eigen[0, 6, 4] == -1.7438
    assert eigen[1, 0, 0] == -6.2357
    assert eigen[1, 0, 15] == 5.8946
    assert eigen[1, 6, 4] == -1.7432
    assert occ[0, 0, 0] == 1.0
    assert occ[0, 0, 15] == 0.6955
    assert occ[0, 6, 4] == 1.0
    assert occ[1, 0, 0] == 1.0
    assert occ[1, 0, 15] == 0.6938
    assert occ[1, 6, 4] == 1.0


def test_toten_result(parse_result):
    """Check that the total energy are of type ArrayData and
    that the entries are as expected.

    """

    from aiida.orm import DataFactory
    _, nodes = parse_result(folder="basic")
    out = nodes['output_energies']
    # test object
    assert isinstance(out, DataFactory('array'))
    energies = out.get_array('toten_0')
    # test number of entries
    assert energies.shape == (1,)
    # check energy
    assert energies[0] == -42.91113621


def test_totens_relax_result(parse_result):
    """Check that the total energies are of type ArrayData and
    that the entries are as expected.

    """

    from aiida.orm import DataFactory
    _, nodes = parse_result(folder="relax")
    out = nodes['output_energies']
    # test object
    assert isinstance(out, DataFactory('array'))
    energies = out.get_array('toten_0')
    # test number of entries
    assert energies.shape == (19,)
    # test a few entries
    assert energies[0] == -42.91113348
    assert energies[3] == -43.37734069
    assert energies[-1] == -43.39087657


def test_hessian_result(parse_result):
    """Check that the Hessian matrix are of type ArrayData and
    that the entries are as expected.

    """

    from aiida.orm import DataFactory
    _, nodes = parse_result(folder="disp")
    out = nodes['output_hessian']
    # test object
    assert isinstance(out, DataFactory('array'))
    hessian = out.get_array('hessian')
    # test shape
    assert hessian.shape == (24, 24)
    # test a few entries
    assert np.all(hessian[0] == np.array([-4.63550410e-01,
                                          0.00000000e+00,
                                          0.00000000e+00,
                                          -5.91774100e-02,
                                          0.00000000e+00,
                                          0.00000000e+00,
                                          3.09711000e-02,
                                          0.00000000e+00,
                                          0.00000000e+00,
                                          3.20435400e-02,
                                          0.00000000e+00,
                                          0.00000000e+00,
                                          1.15129840e-01,
                                          -8.16138200e-02,
                                          8.17234700e-02,
                                          1.14879520e-01,
                                          8.11324800e-02,
                                          8.27409500e-02,
                                          1.14879520e-01,
                                          -8.11324800e-02,
                                          -8.27409500e-02,
                                          1.15129840e-01,
                                          8.16138200e-02,
                                          -8.17234700e-02]))
    assert np.all(hessian[-2] == np.array([8.16138200e-02,
                                           1.15195590e-01,
                                           -8.38411100e-02,
                                           -8.17234700e-02,
                                           1.14875090e-01,
                                           -8.53388100e-02,
                                           3.46686900e-02,
                                           7.00672700e-02,
                                           2.54288300e-02,
                                           -8.26222700e-02,
                                           1.16185510e-01,
                                           7.95575600e-02,
                                           -3.05970000e-04,
                                           3.16827300e-02,
                                           2.86379000e-03,
                                           5.42080000e-04,
                                           3.27613500e-02,
                                           1.12576000e-03,
                                           -1.34305000e-03,
                                           -5.86811100e-02,
                                           2.83374000e-03,
                                           4.91688400e-02,
                                           -4.22101090e-01,
                                           5.73736900e-02]))


def test_dynmat_result(parse_result):
    """Check that the dynamical eigenvectors and eigenvalues
    are of type ArrayData and that the entries are as expected.

    """

    from aiida.orm import DataFactory
    _, nodes = parse_result(folder="disp")
    out = nodes['output_dynmat']
    # test object
    assert isinstance(out, DataFactory('array'))
    dynvec = out.get_array('dynvec')
    dyneig = out.get_array('dyneig')
    # test shape
    assert dynvec.shape == (24, 24)
    assert dyneig.shape == (24,)
    # test a few entries
    assert np.all(dynvec[0] == np.array([7.28517310e-17,
                                         7.25431601e-02,
                                         -4.51957676e-02,
                                         1.15412776e-16,
                                         4.51957676e-02,
                                         -7.25431601e-02,
                                         -1.37347223e-16,
                                         5.16257351e-01,
                                         -5.16257351e-01,
                                         8.16789156e-17,
                                         8.95098005e-02,
                                         -8.95098005e-02,
                                         -4.43838008e-17,
                                         -6.38031134e-02,
                                         6.38031134e-02,
                                         -1.80132830e-01,
                                         -2.97969516e-01,
                                         2.97969516e-01,
                                         1.80132830e-01,
                                         -2.97969516e-01,
                                         2.97969516e-01,
                                         -2.09989969e-16,
                                         -6.38031134e-02,
                                         6.38031134e-02]))
    assert np.all(dynvec[4] == np.array([-5.29825122e-13,
                                         -2.41759046e-01,
                                         -3.28913434e-01,
                                         -5.30734671e-13,
                                         -3.28913434e-01,
                                         -2.41759046e-01,
                                         3.26325910e-13,
                                         -3.80807441e-02,
                                         -3.80807441e-02,
                                         -9.22956103e-13,
                                         -2.99868012e-01,
                                         -2.99868012e-01,
                                         1.64418993e-01,
                                         1.81002749e-01,
                                         1.81002749e-01,
                                         3.11984195e-13,
                                         2.73349550e-01,
                                         2.73349550e-01,
                                         2.59853610e-13,
                                         2.73349550e-01,
                                         2.73349550e-01,
                                         -1.64418993e-01,
                                         1.81002749e-01,
                                         1.81002749e-01]))
    assert dyneig[0] == -1.36621537e+00
    assert dyneig[4] == -8.48939361e-01


# # def test_res(parse_result):
# #    """Check that the results manager can find scalar / low dim results."""
# #    _, nodes = parse_result()
# #    print(nodes['output_parameters'])
# #    output_data = nodes['output_parameters'].get_dict()
# #    assert output_data['energy'] == -459.8761413
# #    assert output_data['efermi'] == 2.96801422
# #    assert 'stress' in output_data
# #    assert 'dielectric tensor' not in output_data


# # def test_no_born(parse_result):
# #    """Make sure no born charges output node exists if lepsilon is not True"""
# #    _, nodes = parse_result()
# #    assert 'born_charges' not in nodes


# # def test_bands(parse_result):
# #    """Check that bands are parsed and have the right shape."""
# #    _, nodes = parse_result()
# #    bands = nodes['output_band']
# #    assert bands.get_bands().shape == (1, 2, 452)


# # def test_dos(parse_result):
# #    """Check that dos are parsed."""
# #    _, nodes = parse_result()
# #    dos = nodes['output_dos']
# #    name, array, units = dos.get_y()[0]
# #    assert name == 'dos_spin_up'
# #    assert array.shape == (301,)
# #    assert units == 'states/eV'


# # def test_suppress_options(parse_result):
# #    """Test that suppress options work."""
# #    _, nodes = parse_result(parser={'parse_dos': False, 'parse_bands': False})
# #    assert 'output_dos' not in nodes
# #    assert 'output_band' not in nodes


# #@pytest.mark.parametrize(['vasprun_path', 'parse_result'], [(2331, False)], indirect=True)
# # def test_slightly_broken_vasprun(parse_result, recwarn):
# #    """Test that truncated vasprun (after one ionic step) can be read and warnings are emitted."""
# #    success, nodes = parse_result()
# #    assert success
# #    assert 'output_kpoints' in nodes
# #    assert 'output_structure' in nodes
# #    assert len(recwarn) >= 1


# #@pytest.mark.parametrize(['vasprun_path', 'parse_result'], [(2331, True)], indirect=True)
# # def test_broken_vasprun_exception(parse_result):
# #    """Test that the parser raises an error with exception_on_bad_xml=True."""
# #    with pytest.raises(ParsingError):
# #        _ = parse_result()  # noqa: F841


# # def test_born_charges(parse_nac, recwarn):
# #    """Test that the born effective charges get parsed."""
# #    success, nodes = parse_nac()
# #    assert success
# #    output_data = nodes['output_parameters'].get_dict()
# #    assert np.all(output_data['dielectric tensor'] == np.array([[5.894056, 0.0, 0.0], [0.0, 5.894056, 0.0], [0.0, 0.0, 6.171821]]))
# #    assert nodes['born_charges'].get_array('born_charges').shape == (26, 3, 3)
# #    assert len(recwarn) >= 1
