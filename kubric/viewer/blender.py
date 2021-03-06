# Copyright 2020 The Kubric Authors
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Implementation of blender backend."""

import bpy
from kubric.viewer import interface


# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------


class NotImplementableError(NotImplementedError):
  """When a method in the interface cannot be realized in a particular implementation."""
  pass


# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------


class Object3D(interface.Object3D):
  # Mapping from interface properties to blender properties (used in keyframing).
  _member_to_blender_data_path = {
      "position": "location",
      "quaternion": "rotation_quaternion"
  }

  def __init__(self, blender_object):  # , name=None):
    super().__init__(self)
    self._blender_object = blender_object
    self._blender_object.rotation_mode = 'QUATERNION'
    # if self.name: self._blender_object.name = self.name

  def _set_position(self, value):
    # (UI: click mesh > Transform > Location)
    super()._set_position(value)
    self._blender_object.location = self.position

  def _set_scale(self, value):
    # (UI: click mesh > Transform > Scale)
    super()._set_scale(value)
    self._blender_object.scale = self.scale

  def _set_quaternion(self, value):
    # (UI: click mesh > Transform > Rotation)
    super()._set_quaternion(value)
    self._blender_object.rotation_quaternion = self.quaternion

  def keyframe_insert(self, member: str, frame: int):
    assert hasattr(self, member), "cannot keyframe an undefined property"
    data_path = Object3D._member_to_blender_data_path[member]
    self._blender_object.keyframe_insert(data_path=data_path, frame=frame)


# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------


class Scene(interface.Scene):
  # TODO: create a named scene, and refer via bpy.data.scenes['Scene']

  def __init__(self):
    super().__init__()
    bpy.context.scene.render.fps = 24
    bpy.context.scene.render.fps_base = 1.0

  def _set_frame_start(self, value):
    super()._set_frame_start(value)
    bpy.context.scene.frame_start = value

  def _set_frame_end(self, value):
    super()._set_frame_end(value)
    bpy.context.scene.frame_end = value

  def add_from_file(self, path: str, axis_forward='Y', axis_up='Z', name=None) -> Object3D:
    bpy.ops.import_scene.obj(filepath=str(path), axis_forward=axis_forward, axis_up=axis_up)
    # WARNING: bpy.context.object does not work here...
    blender_objects = bpy.context.selected_objects[:]
    assert len(blender_objects) == 1
    blender_object = blender_objects[0]
    if name:
        blender_object.name = name
    return Object3D(blender_objects[0])

  def add(self, obj):
    bpy.context.scene.collection.objects.link(obj._blender_object)

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------                                       


class Camera(interface.Camera, Object3D):
  def __init__(self, name='Camera'):
    self.camera = bpy.data.cameras.new(name)
    cam_obj = bpy.data.objects.new(name, self.camera)

    Object3D.__init__(self, cam_obj)


class PerspectiveCamera(interface.PerspectiveCamera, Camera):
  def __init__(self, name='Camera', focal_length=50.):
    Camera.__init__(self, name)
    interface.PerspectiveCamera.__init__(self, focal_length)
    self.camera.type = 'PERSP'
    self.camera.lens = focal_length


class OrthographicCamera(interface.OrthographicCamera, Camera):
  def __init__(self, left=-1, right=+1, top=+1, bottom=-1, near=.1, far=2000):
    interface.OrthographicCamera.__init__(self, left, right, top, bottom, near,
                                          far)
    Camera.__init__(self)
    # --- extra things to set
    self.camera.type = 'ORTHO'
    self.camera.ortho_scale = (right - left)


# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------

# TODO: maybe deprecate in favor of renderer.set_up_background since it does the same but better
class AmbientLight(interface.AmbientLight):
  def __init__(self, color=0x030303, intensity=1):
    interface.AmbientLight.__init__(self, color=color, intensity=intensity)

  def _set_color(self, value):
    super()._set_color(value)
    bpy.context.scene.world.node_tree.nodes["Background"].inputs[
      'Color'].default_value = self.color

  def _set_intensity(self, value):
    super()._set_intensity(value)
    bpy.context.scene.world.node_tree.nodes["Background"].inputs[
      'Strength'].default_value = self.intensity


# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------


class DirectionalLight(interface.DirectionalLight, Object3D):
  def __init__(self, color=0xffffff, intensity=1, shadow_softness=.1):
    self.sun = bpy.data.lights.new('Sun', 'SUN')
    sun_obj = bpy.data.objects.new('Sun', self.sun)
    Object3D.__init__(self, sun_obj)

    interface.DirectionalLight.__init__(self, color=color, intensity=intensity,
                                        shadow_softness=shadow_softness)

  def _set_color(self, value):
    super()._set_color(value)
    self.sun.color = self.color[:3]  # ignore alpha

  def _set_intensity(self, value):
    super()._set_intensity(value)
    self.sun.energy = self.intensity

  def _set_shadow_softness(self, value):
    super()._set_shadow_softness(value)
    self.sun.angle = self.shadow_softness


class RectAreaLight(interface.RectAreaLight, Object3D):
  def __init__(self, color=0xffffff, intensity=1, width=.1, height=0.1):
    self.area = bpy.data.lights.new('Area', 'AREA')
    self.area.shape = 'RECTANGLE'
    area_obj = bpy.data.objects.new('Area', self.area)
    Object3D.__init__(self, area_obj)

    interface.RectAreaLight.__init__(self, color=color, intensity=intensity,
                                     width=width, height=height)

  def _set_width(self, value):
    super()._set_width(value)
    self.area.size = value

  def _set_height(self, value):
    super()._set_height(value)
    self.area.size_y = value

  def _set_color(self, value):
    super()._set_color(value)
    self.area.color = self.color[:3]  # ignore alpha

  def _set_intensity(self, value):
    super()._set_intensity(value)
    self.area.energy = self.intensity


# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------


class BufferAttribute(interface.BufferAttribute):
  pass


class Float32BufferAttribute(interface.Float32BufferAttribute):
  def __init__(self, array, itemSize, normalized=None):
    self.array = array  # TODO: @property


# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------


class Geometry():
  pass


class BoxGeometry(interface.BoxGeometry, Geometry):
  def __init__(self, width=1.0, height=1.0, depth=1.0):
    assert width == height and width == depth, "blender only creates unit cubes"
    interface.BoxGeometry.__init__(self, width=width, height=height,
                                   depth=depth)
    bpy.ops.mesh.primitive_cube_add(size=width)
    self._blender_object = bpy.context.object


class PlaneGeometry(interface.Geometry, Geometry):
  def __init__(self, width: float = 1, height: float = 1,
      widthSegments: int = 1, heightSegments: int = 1):
    assert widthSegments == 1 and heightSegments == 1, "not implemented"
    bpy.ops.mesh.primitive_plane_add()
    self._blender_object = bpy.context.object


class BufferGeometry(interface.BufferGeometry, Geometry):
  def __init__(self):
    interface.BufferGeometry.__init__(self)

  def set_index(self, nparray):
    interface.BufferGeometry.set_index(self, nparray)

  def set_attribute(self, name, attribute: interface.BufferAttribute):
    interface.BufferGeometry.set_attribute(self, name, attribute)


# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------


class Material(interface.Material):
  def __init__(self, specs={}):
    # TODO: is this the same as object3D? guess not?
    self._blender_material = bpy.data.materials.new('Material')

  def blender_apply(self, blender_object):
    """Used by materials that need to access the blender object."""
    pass


class MeshBasicMaterial(interface.MeshBasicMaterial, Material):
  def __init__(self, specs={}):
    Material.__init__(self, specs)
    interface.MeshBasicMaterial.__init__(self, specs)


class MeshPhongMaterial(interface.MeshPhongMaterial, Material):
  def __init__(self, specs={}):
    Material.__init__(self, specs)
    interface.Material.__init__(self, specs=specs)
    # TODO: apply specs

  def blender_apply(self, blender_object):
    bpy.context.view_layer.objects.active = blender_object
    bpy.ops.object.shade_smooth()


class MeshFlatMaterial(interface.MeshFlatMaterial, Material):
  def __init__(self, specs={}):
    Material.__init__(self, specs)
    interface.Material.__init__(self, specs=specs)

  def blender_apply(self, blender_object):
    bpy.context.view_layer.objects.active = blender_object
    bpy.ops.object.shade_flat()


class ShadowMaterial(interface.ShadowMaterial, Material):
  def __init__(self, specs={}):
    Material.__init__(self, specs=specs)
    interface.ShadowMaterial.__init__(self, specs=specs)

  def blender_apply(self, blender_object):
    if self.receive_shadow:
      blender_object.cycles.is_shadow_catcher = True


# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------


class Mesh(interface.Mesh, Object3D):
  def __init__(self, geometry: Geometry, material: Material):
    interface.Mesh.__init__(self, geometry, material)

    # --- Create the blender object
    # WARNING: differently from threejs, blender creates an object when
    # primivitives are created, so we need to make sure we do not duplicate it
    if hasattr(geometry, "_blender_object"):
      # TODO: is there a better way to achieve this?
      Object3D.__init__(self, geometry._blender_object)
    else:
      bpy.ops.object.add(type="MESH")
      Object3D.__init__(self, bpy.context.object)

    # --- Assigns the buffers to the object
    # TODO: is there a better way to achieve this?
    if isinstance(self.geometry, BufferGeometry):
      vertices = self.geometry.attributes["position"].array.tolist()
      faces = self.geometry.index.tolist()
      self._blender_object.data.from_pydata(vertices, [], faces)

    # --- Adds the material to the object
    self._blender_object.data.materials.append(material._blender_material)
    self.material.blender_apply(self._blender_object)


# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------


class Renderer(interface.Renderer):

  def __init__(self, useBothCPUGPU=False):
    super().__init__()
    self.clear_scene()  # as blender has a default scene on load
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.samples = 128
    bpy.context.scene.cycles.max_bounces = 6
    bpy.context.scene.cycles.film_exposure = 1.5


    # activate further render passes
    view_layer = bpy.context.scene.view_layers['View Layer']
    view_layer.cycles.use_denoising = True
    view_layer.use_pass_vector = True  # flow
    view_layer.use_pass_uv = True  # UV
    view_layer.use_pass_normal = True  # surface normals
    view_layer.cycles.use_pass_crypto_object = True  # segmentation
    view_layer.cycles.pass_crypto_depth = 2

    # --- compute devices
    # derek, why is the rationale? → rendering on GPU only sometime faster than CPU+GPU
    # TODO: modify the logic to execute on CPU, GPU, CPU+GPU
    cyclePref = bpy.context.preferences.addons['cycles'].preferences
    cyclePref.compute_device_type = 'CUDA'
    for dev in cyclePref.devices:
      if dev.type == "CPU" and useBothCPUGPU is False:
        dev.use = False
      else:
        dev.use = True
    bpy.context.scene.cycles.device = 'GPU'
    for dev in cyclePref.devices:
      print(dev)
      print(dev.use)

  def set_background_transparent(self, film_transparent: bool):
    bpy.context.scene.render.film_transparent = film_transparent

  def set_size(self, width: int, height: int):
    super().set_size(width, height)
    bpy.context.scene.render.resolution_x = self.width
    bpy.context.scene.render.resolution_y = self.height

  def set_clear_color(self, color: int, alpha: float):
    raise NotImplementableError()

  def clear_scene(self):
    bpy.ops.wm.read_homefile()
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

  def default_camera_view(self):
    """Changes the UI so that the default view is from the camera POW."""
    view3d = next(
        area for area in bpy.context.screen.areas if area.type == 'VIEW_3D')
    view3d.spaces[0].region_3d.view_perspective = 'CAMERA'

  def set_up_exr_output(self, path):
    bpy.context.scene.use_nodes = True
    tree = bpy.context.scene.node_tree
    links = tree.links
    render_node = tree.nodes.get('Render Layers')

    # create a new FileOutput node
    out_node = tree.nodes.new(type='CompositorNodeOutputFile')
    # set the format to EXR (multilayer)
    out_node.format.file_format = 'OPEN_EXR_MULTILAYER'
    out_node.base_path = path  # output directory

    layers = ['Image', 'Depth', 'Vector', 'UV', 'Normal', 'CryptoObject00']

    out_node.file_slots.clear()
    for l in layers:
      out_node.file_slots.new(l)
      links.new(render_node.outputs.get(l), out_node.inputs.get(l))

  def set_up_background(self, hdri_filepath=None, bg_color=None,
                             hdri_rotation=(0.0, 0.0, 0.0)):
    """
    Use an HDRI file for global illumination, and/or render background with solid color.



    Args:
      hdri_filepath (str): path to the HDRI file.
      bg_color: RGBA value of rendered background color.
      hdri_rotation: XYZ euler angles for rotating the HDRI image.
    """
    assert hdri_filepath is not None or bg_color is not None

    bpy.context.scene.world.use_nodes = True
    tree = bpy.context.scene.world.node_tree
    links = tree.links

    # clear the tree
    for node in tree.nodes.values():
      tree.nodes.remove(node)

    # create nodes
    out_node = tree.nodes.new(type='ShaderNodeOutputWorld')
    out_node.location = 1100, 0

    if hdri_filepath is not None:
      coord_node = tree.nodes.new(type='ShaderNodeTexCoord')
      mapping_node = tree.nodes.new(type='ShaderNodeMapping')
      mapping_node.location = 200, 0
      hdri_node = tree.nodes.new(type='ShaderNodeTexEnvironment')
      hdri_node.location = 400, 0
      light_bg_node = tree.nodes.new(type='ShaderNodeBackground')
      light_bg_node.location = 700, 0

      # link nodes
      links.new(coord_node.outputs.get('Generated'), mapping_node.inputs.get('Vector'))
      links.new(mapping_node.outputs.get('Vector'), hdri_node.inputs.get('Vector'))
      links.new(hdri_node.outputs.get('Color'), light_bg_node.inputs.get('Color'))

      # load the actual image
      hdri_node.image = bpy.data.images.load(hdri_filepath, check_existing=True)
      # set the rotation
      mapping_node.inputs.get('Rotation').default_value = hdri_rotation  # XYZ rotation of HDRI bg

      # if no background color is set, then connect to output node
      if bg_color is None:
        links.new(light_bg_node.outputs.get('Background'), out_node.inputs.get('Surface'))

    if bg_color is not None:
      camera_bg_node = tree.nodes.new(type='ShaderNodeBackground')
      camera_bg_node.location = 700, -120
      # set bg color value
      camera_bg_node.inputs.get('Color').default_value = bg_color  # BG color RGBA

      # if no HDRI image is set, then connect to output node
      if hdri_filepath is None:
        links.new(camera_bg_node.outputs.get('Background'), out_node.inputs.get('Surface'))

    # if both are set, then use a mixing node and a lightpath input
    if hdri_filepath is not None and bg_color is not None:
      mix_node = tree.nodes.new(type='ShaderNodeMixShader')
      mix_node.location = 900, 0
      lightpath_node = tree.nodes.new(type='ShaderNodeLightPath')
      lightpath_node.location = 700, 350

      links.new(lightpath_node.outputs.get('Is Camera Ray'), mix_node.inputs.get('Fac'))
      links.new(light_bg_node.outputs.get('Background'), mix_node.inputs[1])
      links.new(camera_bg_node.outputs.get('Background'), mix_node.inputs[2])
      links.new(mix_node.outputs.get('Shader'), out_node.inputs.get('Surface'))

  def render(self, scene: Scene, camera: Camera, path: str,
      on_render_write=None):
    # --- adjusts resolution according to threejs style camera
    if isinstance(camera, OrthographicCamera):
      aspect = (camera.right - camera.left) * 1.0 / (camera.top - camera.bottom)
      new_y_res = int(bpy.context.scene.render.resolution_x / aspect)
      if new_y_res != bpy.context.scene.render.resolution_y:
        print("WARNING: blender renderer adjusted the film resolution", end="")
        print(new_y_res, bpy.context.scene.render.resolution_y)
        bpy.context.scene.render.resolution_y = new_y_res

    # --- Sets the default camera
    bpy.context.scene.camera = camera._blender_object

    if not path.endswith(".blend"):
      bpy.context.scene.render.filepath = path

    # --- creates blender file
    if path.endswith(".blend"):
      self.default_camera_view()  # TODO: not saved... why?
      bpy.ops.wm.save_mainfile(filepath=path)

    # --- renders a movie
    elif path.endswith(".mov"):
      # WARNING: movies do not support transparency
      # TODO: actually they do, ask @bydeng for the needed blender config.
      assert bpy.context.scene.render.film_transparent == False
      bpy.context.scene.render.image_settings.file_format = "FFMPEG"
      bpy.context.scene.render.image_settings.color_mode = "RGB"
      bpy.context.scene.render.ffmpeg.format = "QUICKTIME"
      bpy.context.scene.render.ffmpeg.codec = "H264"

    # --- renders one frame directly to a png file
    elif path.endswith(".png"):
      # TODO: add capability bpy.context.scene.frame_set(frame_number)
      bpy.ops.render.render(write_still=True, animation=False)

    # --- creates a movie as a image sequence {png}
    else:
      if on_render_write:
        bpy.app.handlers.render_write.append(
          lambda scene: on_render_write(scene.render.frame_path()))
      # Convert to gif via ImageMagick: `convert -delay 8 -loop 0 *.png output.gif`
      bpy.ops.render.render(write_still=True, animation=True)
