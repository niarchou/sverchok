# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

import math
from random import random

import bpy
from bpy.props import StringProperty, BoolProperty, EnumProperty
import bmesh
from mathutils import Vector

from sverchok.node_tree import SverchCustomTreeNode
from sverchok.data_structure import updateNode
from sverchok.utils.sv_viewer_utils import matrix_sanitizer


def wipe_object(ob):
    ''' this removes all geometry '''
    bm = bmesh.new()
    bm.to_mesh(ob.data)
    bm.free()


class SvDupliInstancesMK3(bpy.types.Node, SverchCustomTreeNode):
    bl_idname = 'SvDupliInstancesMK3'
    bl_label = 'Dupli Instances MK3'
    bl_icon = 'OUTLINER_OB_EMPTY'

    name_node_generated_parent = StringProperty(
        description="name of the parent that this node generates",
        update=updateNode)

    name_child = StringProperty(
        description="name of object to duplicate",
        update=updateNode)

    def sv_init(self, context):
        self.inputs.new("VerticesSocket", "Locations")
        self.inputs.new("MatrixSocket", "Transforms")
        self.name_node_generated_parent = 'booom'

    def draw_buttons(self, context, layout):
        col = layout.column()
        col.prop(self, 'name_node_generated_parent', text='', icon='LOOPSEL')
        col.prop_search(self, 'name_child', bpy.data, 'objects', text='')

    def process(self):
        locations = self.inputs['Locations'].sv_get(default=None)
        transforms = self.inputs['Transforms'].sv_get(default=None)

        objects = bpy.data.objects
        ob = objects.get(self.name_node_generated_parent)

        if ob:
            wipe_object(ob)

        # minimum requirements.
        if (not any([locations, transforms])) or (not self.name_child):
            if ob:
                ob.dupli_type = 'NONE'
            return

        if not ob:
            name = self.name_node_generated_parent
            mesh = bpy.data.meshes.new(name + '_mesh')
            ob = bpy.data.objects.new(name, mesh)
            bpy.context.scene.objects.link(ob)

        # at this point there's a reference to an ob, and the mesh is empty.
        child = objects.get(self.name_child)

        if locations and locations[0] and (not transforms):
            locations = locations[0]
            # -- this mode will vertex duplicate --
            ob.data.from_pydata(locations, [], [])
            ob.dupli_type = 'VERTS'
            child.parent = ob

        elif transforms:
            # -- this mode will face duplicate --
            # i expect this can be done faster using numpy
            # please view this only as exploratory
            scale = 1
            theta = 2 * math.pi / 3
            thetb = theta * 2
            ofs = 0.5 * math.pi + theta
            A = math.cos(0 + ofs) * scale, math.sin(0 + ofs) * scale, 0
            B = math.cos(theta + ofs) * scale, math.sin(theta + ofs) * scale, 0
            C = math.cos(thetb + ofs) * scale, math.sin(thetb + ofs) * scale, 0
            verts = []
            add_verts = verts.extend
            num_matrices = len(transforms)
            for m in transforms:
                M = matrix_sanitizer(m)
                a = (M * Vector(A))[:]
                b = (M * Vector(B))[:]
                c = (M * Vector(C))[:]
                add_verts([a, b, c])

            strides = range(0, num_matrices * 3, 3)
            faces = [[i, i + 1, i + 2] for i in strides]

            ob.data.from_pydata(verts, [], faces)
            ob.dupli_type = 'FACES'
            ob.use_dupli_faces_scale = True
            child.parent = ob


def register():
    bpy.utils.register_class(SvDupliInstancesMK3)


def unregister():
    bpy.utils.unregister_class(SvDupliInstancesMK3)
