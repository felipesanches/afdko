from __future__ import print_function, division, absolute_import

import os
import pytest
import subprocess32 as subprocess
import tempfile

from fontTools.ttLib import TTFont

from .runner import main as runner
from .differ import main as differ
from .differ import SPLIT_MARKER

TOOL = 'makeotfexe'
CMD = ['-t', TOOL]

data_dir_path = os.path.join(os.path.split(__file__)[0], TOOL + '_data')


def _get_expected_path(file_name):
    return os.path.join(data_dir_path, 'expected_output', file_name)


def _get_input_path(file_name):
    return os.path.join(data_dir_path, 'input', file_name)


def _get_temp_file_path():
    file_descriptor, path = tempfile.mkstemp()
    os.close(file_descriptor)
    return path


def _generate_ttx_dump(font_path, tables=None):
    with TTFont(font_path) as font:
        temp_path = _get_temp_file_path()
        font.saveXML(temp_path, tables=tables)
        return temp_path


# -----
# Tests
# -----

def test_exit_no_option():
    # It's valid to run 'makeotfexe' without using any options,
    # but if a default-named font file ('font.ps') is NOT found
    # in the current directory, the tool exits with an error
    with pytest.raises(subprocess.CalledProcessError) as err:
        subprocess.check_call([TOOL])
    assert err.value.returncode == 1


@pytest.mark.parametrize('arg', ['-h', '-u'])
def test_exit_known_option(arg):
    assert subprocess.call([TOOL, arg]) == 0


@pytest.mark.parametrize('arg', ['j', 'bogus'])
def test_exit_unknown_option(arg):
    assert subprocess.call([TOOL, arg]) == 1


@pytest.mark.parametrize('caret_format', [
    'bypos', 'byindex', 'mixed', 'mixed2', 'double', 'double2'])
def test_GDEF_LigatureCaret_bug155(caret_format):
    input_filename = 'bug155/font.pfa'
    feat_filename = 'bug155/caret-{}.fea'.format(caret_format)
    ttx_filename = 'bug155/caret-{}.ttx'.format(caret_format)
    actual_path = _get_temp_file_path()
    runner(CMD + ['-o', 'f', '_{}'.format(_get_input_path(input_filename)),
                        'ff', '_{}'.format(_get_input_path(feat_filename)),
                        'o', '_{}'.format(actual_path)])
    actual_ttx = _generate_ttx_dump(actual_path, ['GDEF'])
    expected_ttx = _get_expected_path(ttx_filename)
    assert differ([expected_ttx, actual_ttx, '-l', '2'])


def test_useMarkFilteringSet_flag_bug196():
    input_filename = "bug196/font.pfa"
    feat_filename = "bug196/feat.fea"
    actual_path = _get_temp_file_path()
    ttx_filename = "bug196.ttx"
    runner(CMD + ['-o', 'f', '_{}'.format(_get_input_path(input_filename)),
                        'ff', '_{}'.format(_get_input_path(feat_filename)),
                        'o', '_{}'.format(actual_path)])
    actual_ttx = _generate_ttx_dump(actual_path, ['GSUB'])
    expected_ttx = _get_expected_path(ttx_filename)
    assert differ([expected_ttx, actual_ttx, '-s', '<ttFont sfntVersion'])


def test_mark_refer_diff_classes_bug416():
    input_filename = "bug416/font.pfa"
    feat_filename = "bug416/feat.fea"
    actual_path = _get_temp_file_path()
    ttx_filename = "bug416.ttx"
    runner(CMD + ['-o', 'f', '_{}'.format(_get_input_path(input_filename)),
                        'ff', '_{}'.format(_get_input_path(feat_filename)),
                        'o', '_{}'.format(actual_path)])
    actual_ttx = _generate_ttx_dump(actual_path, ['GPOS'])
    expected_ttx = _get_expected_path(ttx_filename)
    assert differ([expected_ttx, actual_ttx, '-s', '<ttFont sfntVersion'])


def test_DFLT_script_with_any_lang_bug438():
    """ The feature file bug438/feat.fea contains languagesystem
    statements for a language other than 'dflt' with the 'DFLT' script
    tag. With the fix, makeotfexe will build an OTF which is identical to
    'bug438.ttx'. Without the fix, it will fail to build an OTF."""
    input_filename = 'bug438/font.pfa'
    feat_filename = 'bug438/feat.fea'
    ttx_filename = 'bug438.ttx'
    actual_path = _get_temp_file_path()
    runner(CMD + ['-o', 'f', '_{}'.format(_get_input_path(input_filename)),
                        'ff', '_{}'.format(_get_input_path(feat_filename)),
                        'o', '_{}'.format(actual_path)])
    actual_ttx = _generate_ttx_dump(actual_path)
    expected_ttx = _get_expected_path(ttx_filename)
    assert differ([expected_ttx, actual_ttx,
                   '-s',
                   '<ttFont sfntVersion' + SPLIT_MARKER +
                   '    <checkSumAdjustment value=' + SPLIT_MARKER +
                   '    <checkSumAdjustment value=' + SPLIT_MARKER +
                   '    <created value=' + SPLIT_MARKER +
                   '    <modified value=',
                   '-r', r'^\s+Version.*;hotconv.*;makeotfexe'])


@pytest.mark.parametrize('feat_name, error_msg', [
    ('test_named_lookup',
        b"[FATAL] <SourceSans-Test> In feature 'last' positioning rules "
        b"cause an offset overflow (0x10020) to a lookup subtable"),
    ('test_singlepos_subtable_overflow',
        b"[FATAL] <SourceSans-Test> In feature 'sps1' lookup 'lkup40' "
        b"positioning rules cause an offset overflow (0x10188) to a "
        b"lookup subtable"),
    ('test_class_pair_subtable_overflow',
        b"[FATAL] <SourceSans-Test> In feature 'last' positioning rules "
        b"cause an offset overflow (0x10020) to a lookup subtable"),
    ('test_class_pair_class_def_overflow',
        b"[FATAL] <SourceSans-Test> In feature 'krn1' lookup 'l1' pair "
        b"positioning rules cause an offset overflow (0x1001a) to a "
        b"class 2 definition table"),
    ('test_contextual_overflow',
        b"[FATAL] <SourceSans-Test> In feature 'krn0' lookup 'lkup40' "
        b"chain contextual positioning rules cause an offset overflow "
        b"(0x10002) to a lookup subtable"),
    ('test_cursive_subtable_overflow',
        b"[FATAL] <SourceSans-Test> In feature 'curs' lookup 'lk20' "
        b"cursive positioning rules cause an offset overflow "
        b"(0x1006e) to a cursive attach table"),
    ('test_mark_to_base_coverage_overflow',
        b"[FATAL] <SourceSans-Test> In feature 'mrk1' mark to base "
        b"positioning rules cause an offset overflow (0x1002c) to a "
        b"base coverage table"),
    ('test_mark_to_base_subtable_overflow',
        b"[FATAL] <SourceSans-Test> In feature 'mrk1' mark to base "
        b"positioning rules cause an offset overflow (0x10230) to a "
        b"lookup subtable"),
    ('test_mark_to_ligature_subtable_overflow',
        b"[FATAL] <SourceSans-Test> In feature 'lig1' lookup 'lk0' mark "
        b"to base positioning rules cause an offset overflow (0x1053e) "
        b"to a lookup subtable"),
    ('test_singlesub1_subtable_overflow',
        b"[FATAL] <SourceSans-Test> In feature 'tss2' lookup 'lkup258' "
        b"substitution rules cause an offset overflow (0x10002) to a "
        b"lookup subtable"),
    ('test_singlesub2_subtable_overflow',
        b"[FATAL] <SourceSans-Test> In feature 'tss1' lookup 'lkup237' "
        b"substitution rules cause an offset overflow (0x10098) to a "
        b"lookup subtable"),
    ('test_multiplesub_subtable_overflow',
        b"[FATAL] <SourceSans-Test> In feature 'mts1' lookup 'lkup238' "
        b"substitution rules cause an offset overflow (0x10056) to a "
        b"lookup subtable"),
    ('test_alternatesub_subtable_overflow',
        b"[FATAL] <SourceSans-Test> In feature 'ats1' lookup 'lkup238' "
        b"substitution rules cause an offset overflow (0x1009c) to a "
        b"lookup subtable"),
    ('test_ligaturesub_subtable_overflow',
        b"[FATAL] <SourceSans-Test> In feature 'lts1' lookup 'lkup238' "
        b"substitution rules cause an offset overflow (0x10016) to a "
        b"lookup subtable"),
    ('test_chaincontextualsub_subtable_overflow',
        b"[FATAL] <SourceSans-Test> In feature 'cts1' substitution rules "
        b"cause an offset overflow (0x100ac) to a lookup subtable"),
    ('test_reversechaincontextualsub_subtable_overflow',
        b"[FATAL] <SourceSans-Test> In feature 'rts1' lookup 'lkup238' "
        b"reverse chain contextual substitution rules cause an offset "
        b"overflow (0x100a0) to a lookup subtable"),
    ('test_duplicate_single_sub',
        b"[NOTE] <SourceSans-Test> Removing duplicate single substitution "
        b"in stand-alone lookup 'test2': glyph1, glyph1"),
    ('test_conflicting_single_sub',
        b"[FATAL] <SourceSans-Test> Duplicate target glyph for single "
        b"substitution in stand-alone lookup 'test2': glyph1"),
    ('test_duplicate_alternate_sub',
        b"[FATAL] <SourceSans-Test> Duplicate target glyph for alternate "
        b"substitution in stand-alone lookup 'test2': glyph1"),
    ('test_duplicate_multiple_sub',
        b"[FATAL] <SourceSans-Test> Duplicate target glyph for multiple "
        b"substitution in stand-alone lookup 'test2': glyph1"),
    ('test_duplicate_ligature_sub',
        b"[NOTE] <SourceSans-Test> Removing duplicate ligature substitution "
        b"in stand-alone lookup 'test2'"),
    ('test_conflicting_ligature_sub',
        b"[FATAL] <SourceSans-Test> Duplicate target sequence but different "
        b"replacement glyphs in ligature substitutions in stand-alone "
        b"lookup 'test2'"),
    ('test_duplicate_single_pos',
        b"[NOTE] <SourceSans-Test> Removing duplicate single positioning "
        b"in stand-alone lookup 'test2'"),
    ('test_conflicting_single_pos',
        b"[FATAL] <SourceSans-Test> Duplicate single positioning glyph "
        b"with different values in stand-alone lookup 'test2'"),
    ('test_features_name_missing_win_dflt_sub',
        b"[FATAL] <SourceSans-Test> Missing Windows default name for "
        b"feature name nameid 256 in feature 'ss01'"),
    ('test_cv_params_not_in_cvxx_sub',
        b"[FATAL] <SourceSans-Test> A 'cvParameters' block is allowed only "
        b"in Character Variant (cvXX) features. It is being used in "
        b"feature 'tst1'"),
    ('test_cv_params_missing_win_dflt_sub',
        b"[FATAL] <SourceSans-Test> Missing Windows default name for "
        b"cvParameters name nameid 256 in feature 'cv01'"),
    ('test_size_withfamilyID_0_pos',
        b"[FATAL] <SourceSans-Test> size feature must have 4 parameters if "
        b"sub family ID code is non-zero!"),
    ('test_size_withfamilyID_3_pos',
        b"[FATAL] <SourceSans-Test> size feature must have 4 or 2 parameters "
        b"if sub family code is zero!"),
    ('test_sizemenuname_missing_win_dflt_pos',
        b"[FATAL] <SourceSans-Test> Missing Windows default name for "
        b"sizemenuname nameid 256 in feature 'size'"),
    ('test_kernpair_warnings_pos',
        b"[WARNING] <SourceSans-Test> Single kern pair occurring after class "
        b"kern pair in feature 'tst1'"),
    ('test_kernpair_warnings_pos',
        b"[WARNING] <SourceSans-Test> Start of new pair positioning subtable "
        b"forced by overlapping glyph classes in feature 'tst1'; some pairs "
        b"may never be accessed"),
    ('test_kernpair_warnings_pos',
        b"[NOTE] <SourceSans-Test> Removing duplicate pair positioning in "
        b"feature 'tst1': glyph3 glyph3"),
    ('test_kernpair_warnings_pos',
        b"[WARNING] <SourceSans-Test> Pair positioning has conflicting "
        b"statements in feature 'tst1'"),
    ('test_base_glyph_conflict_pos',
        b"[ERROR] <SourceSans-Test> MarkToBase or MarkToMark error in "
        b"feature 'tst1': Another statement has already defined the anchors "
        b"and marks on this the same glyph 'glyph5'."),
    ('test_base_glyph_conflict_pos',
        b"[WARNING] <SourceSans-Test> MarkToBase or MarkToMark error in "
        b"feature 'tst1': The glyph 'glyph5' does not have an anchor point "
        b"for a mark class that was used in a previous statement in the "
        b"same lookup table. Setting the anchor point offset to 0."),
    ('test_mark_ligature_conflict_pos',
        b"[ERROR] <SourceSans-Test> MarkToLigature error in feature 'tst1': "
        b"Two different statements referencing the ligature glyph 'glyph6' "
        b"have assigned the same mark class to the same ligature component."),
    ('test_mark_ligature_conflict_pos',
        b"[ERROR] <SourceSans-Test> MarkToLigature statement in feature "
        b"'tst1' for glyph 'glyph6' contains a duplicate mark class "
        b"assignment for one of the ligature components."),
    ('test_mark_class_glyph_conflict',
        b"[ERROR] <SourceSans-Test> in feature 'tst1', the glyph 'glyph2' "
        b"is repeated in the current class definition.  mark class "
        b"@TOP_MARKS."),
    ('test_mark_class_glyph_conflict',
        b"[ERROR] <SourceSans-Test> In feature 'tst1', Glyph 'glyph1' "
        b"occurs in two different mark classes. Previous mark class: "
        b"@TOP_MARKS. Current mark class @BOTTOM_MARKS."),
    ('test_base_anchor_errors_pos',
        b"[ERROR] <SourceSans-Test> MarkToBase or MarkToMark error in "
        b"feature 'tst1': Another statement has already assigned the current "
        b"mark class to another anchor point on the same glyph 'glyph7'"),
    ('test_base_anchor_errors_pos',
        b"[WARNING] <SourceSans-Test> MarkToBase or MarkToMark error in "
        b"feature 'tst1': The glyph 'glyph5' does not have an anchor point "
        b"for a mark class that was used in a previous statement in the "
        b"same lookup table"),
    ('test_cursive_duplicate_glyph_pos',
        b"[ERROR] <SourceSans-Test> Cursive statement error in feature "
        b"'tst1': A previous statment has already referenced the same "
        b"glyph 'glyph1'."),

])
def test_oveflow_report_bug313(feat_name, error_msg):
    input_filename = 'bug313/font.pfa'
    feat_filename = 'bug313/{}.fea'.format(feat_name)
    otf_path = _get_temp_file_path()

    stderr_path = runner(
        CMD + ['-s', '-e', '-o', 'shw',
               'f', '_{}'.format(_get_input_path(input_filename)),
               'ff', '_{}'.format(_get_input_path(feat_filename)),
               'o', '_{}'.format(otf_path)])

    with open(stderr_path, 'rb') as f:
        output = f.read()
    assert error_msg in output
