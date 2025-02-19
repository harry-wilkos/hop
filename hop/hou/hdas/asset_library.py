from pxr.Usd import Stage, Prim
from hop.hou.util import usd_helpers
from pxr import UsdShade, UsdGeom, UsdLux, Sdf


def check_materials(stage: Stage):
    mats = []
    for prim in usd_helpers.expand_stage(stage):
        if prim.IsA(UsdShade.Material):
            name = prim.GetName()
            if name not in mats:
                mats.append(name)
                continue
            return False
    return True


def resolve_materials(stage: Stage):
    for prim in usd_helpers.expand_stage(stage):
        if prim.IsA(UsdGeom.Boundable) and not UsdLux.LightAPI(prim):
            mat_binding = prim.GetRelationship("material:binding")
            true_target = mat_binding.GetForwardedTargets()
            mat_binding.SetTargets(true_target)
            mat_binding = prim.GetRelationship("material:binding")
            strength = usd_helpers.convert_bind_strength(mat_binding.GetMetadata("bindMaterialAs"))
            if strength:
                print(prim)


# Loop through the collected boundable primitive paths
# for boundable_prim in all_boundable_prims:
#     material_binding_rel = boundable_prim.GetRelationship("material:binding")
#     store_base_binding = material_binding_rel
#     if str(material_binding_rel).startswith("invalid relationship") == True:
#         material_binding_rel = "No_Material"
#         strength_metadata = "No_Strength"
#     else:
#         strength_metadata = material_binding_rel.GetMetadata("bindMaterialAs")
#         #store_binding = material_binding_rel
#         #store_strength = strength_metadata
#     ancestor = boundable_prim.GetParent()
#     x=0
#
#     while ancestor:
#         #print(ancestor)
#         current_binding = ancestor.GetRelationship("material:binding")
#         if str(current_binding).startswith("invalid relationship") == True:
#             pass
#         else:
#             current_strength = current_binding.GetMetadata("bindMaterialAs")
#             if material_binding_rel == "No_Material" and str(current_binding).startswith("invalid relationship") == False:
#                 material_binding_rel = current_binding
#                 strength_metadata = current_strength
#             elif current_strength == None and strength_metadata == None:
#                 pass
#             elif current_strength == None and strength_metadata == "strongerThanDescendants":
#                 pass
#             elif current_strength == None and strength_metadata == "weakerThanDescendants":
#                 #material_binding_rel = current_binding
#                 #strength_metadata = current_strength
#                 #print(ancestor)
#                 #print("test")
#                 pass
#             elif current_strength == "weakerThanDescendants" and strength_metadata == None:
#                 pass
#             elif current_strength == "weakerThanDescendants" and strength_metadata == "strongerThanDescendants":
#                 pass
#             elif current_strength == "weakerThanDescendants" and strength_metadata == "weakerThanDescendants":
#                 pass
#             elif current_strength == "strongerThanDescendants" and strength_metadata == None:
#                 material_binding_rel = current_binding
#                 strength_metadata = current_strength
#             elif current_strength == "strongerThanDescendants" and strength_metadata == "weakerThanDescendants":
#                 material_binding_rel = current_binding
#                 strength_metadata = current_strength
#             elif current_strength == "strongerThanDescendants" and strength_metadata == "strongerThanDescendants":
#                 material_binding_rel = current_binding
#                 strength_metadata = current_strength
#
#             if material_binding_rel == "No_Material":
#                 final_binding = material_binding_rel
#             else:
#                 final_binding = material_binding_rel.GetTargets()
#
#             #print(final_binding)
#         ancestor = ancestor.GetParent()
#         ancestor_str = str(ancestor)
#         if ancestor_str == "Usd.Prim(</>)":
#             break
#         x += 1
#     if material_binding_rel == "No_Material":
#         pass
#         #final_binding = material_binding_rel
#     else:
#         final_binding = material_binding_rel.GetTargets()
#         create_relationship = boundable_prim.CreateRelationship("material:binding")
#         for mat_path in final_binding:
#             #mtl_scope = UsdGeom.Scope.Define(stage, "/mtl")
#             material = stage.GetPrimAtPath(mat_path)
#             Material_Name = material.GetName()
#             Asset_Name = hou.node("../").evalParm("Asset_Name")
#             New_Mat_Path = "/" + Asset_Name + "/mtl/" + Material_Name
#             Material_Trans.append(str(mat_path))
#             #
#             New_rel = create_relationship.SetTargets([Sdf.Path(New_Mat_Path)])
#             create_relationship.SetMetadata("bindMaterialAs", None)

# spaced_string = " ".join(Material_Trans)
# hou.node("../Reparent_Mtl").parm("primpattern").set(str(spaced_string))
# #print(spaced_string)
