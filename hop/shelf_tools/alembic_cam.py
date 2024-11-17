from ..util import alembic, place_node, extract_matrix
from pathlib import Path
import _alembic_hom_extensions as abc
import math
import numpy as np

try:
    import hou
except ModuleNotFoundError:
    from ..util import import_hou

    hou = import_hou()

bindings = [
    "tx",
    "ty",
    "tz",
    "rx",
    "ry",
    "rz",
]

parm_expression = r"""
from hop.shelf_tools import alembic_parm_value
return alembic_parm_value()
"""

xfrom_expression = r"""
from hop.shelf_tools import alembic_transform_value
return alembic_transform_value()
"""


def alembic_transform_value():
    node = hou.pwd()
    parm_name = hou.expandString("$CH")
    file = node.evalParm("alembic_file")
    alembic_path = node.evalParm("alembic_path")
    alembic_file = Path(hou.text.expandString(file)).resolve().as_posix()

    final_transform = np.identity(4)
    current_path = alembic_path
    while current_path:
        xform = abc.getLocalXform(
            alembic_file, current_path, hou.frameToTime(hou.frame() + 1)
        )[0]
        xform_matrix = np.array(xform).reshape((4, 4))
        final_transform = np.dot(final_transform, xform_matrix)
        current_path = "/".join(current_path.split("/")[:-1])

    results = extract_matrix(final_transform)
    value = results[bindings.index(parm_name)]
    if parm_name in bindings[:3]:
        value *= node.evalParm("uni_scale")
    return value


def alembic_parm_value():
    node = hou.pwd()
    parm_name = hou.expandString("$CH")
    file = node.evalParm("alembic_file")
    alembic_file = Path(hou.text.expandString(file)).resolve().as_posix()
    alembic_path = node.evalParm("alembic_path")
    cam_dic = abc.alembicGetCameraDict(
        alembic_file, alembic_path, hou.frameToTime(hou.frame())
    )
    if parm_name in cam_dic:
        value = cam_dic[parm_name]
    else:
        parm = node.parm(parm_name)
        value = parm.parmTemplate().defaultValue()[parm.componentIndex()]
    return value


def import_alembic_cam(kwargs: dict):
    file = hou.ui.selectFile(
        start_directory=None,
        title="Choose Alembic",
        collapse_sequences=False,
        file_type=hou.fileType.Alembic,
        chooser_mode=hou.fileChooserMode.Read,
    )
    if file:
        path = Path(hou.text.expandString(file)).resolve().as_posix()
        cams = alembic.find_cam_paths(path)
        start, end, frame = alembic.frame_info(path)
        if (
            hou.fps() != frame
            or hou.playbar.frameRange()[0] != start
            or hou.playbar.frameRange()[1] != end
        ):
            if hou.ui.displayCustomConfirmation(
                f"Set frame range ({start} - {end}) and fps ({frame}) from alembic?",
                buttons=("No", "Yes"),
                severity=hou.severityType.Message,
                default_choice=0,
                close_choice=0,
                title="Alembic Camera Import",
            ):
                hou.setFps(frame, False)
                hou.playbar.setFrameRange(start, end)
                hou.playbar.setPlaybackRange(start, end)
                if start > hou.frame() or hou.frame() > end:
                    hou.setFrame(start)
        for cam in cams:
            node = place_node(kwargs, "obj", "cam")
            if node is not None:
                template = node.parmTemplateGroup()
                alembic_file = hou.StringParmTemplate(
                    name="alembic_file",
                    label="Alembic File",
                    num_components=1,
                    string_type=hou.stringParmType.FileReference,
                    file_type=hou.fileType.Geometry,
                )
                alembic_path = hou.StringParmTemplate(
                    name="alembic_path", label="Alembic Path", num_components=1
                )
                scale = hou.FloatParmTemplate(
                    name="uni_scale",
                    label="Uniform Scale",
                    num_components=1,
                    default_value=(1.0,),
                )
                template.append(alembic_file)
                template.append(alembic_path)
                template.appendToFolder("Transform", scale)
                node.setParmTemplateGroup(template)
                node.setParms({"alembic_file": file, "alembic_path": cam})
                parms = abc.alembicGetCameraDict(path, cam, 0)
                resx = node.evalParm("resx")
                resy = node.evalParm("resy")
                for xform in bindings:
                    xf_parm = node.parm(xform)
                    xf_parm.setExpression(
                        xfrom_expression, hou.exprLanguage.Python, True
                    )
                for key in parms:
                    parm = node.parm(key)
                    if parm is not None:
                        parm.setExpression(
                            parm_expression, hou.exprLanguage.Python, True
                        )
                    elif key == "filmaspectratio" and not math.isclose(
                        resx / resy, parms[key]
                    ):
                        hou.ui.displayMessage(
                            text=f"{resx} x {resy} is not the same aspect ration as the alembic ({round(parms[key], 2)})",
                            severity=hou.severityType.Warning,
                            title="Alembic camera",
                        )
