bl_info = {
    "name": "Paste PureRef Images",
    "blender": (2, 80, 0),
    "category": "Image",
    "author": "Martin Fir, Tine Maher, The Wall",
    "description": "Paste images from clipboard or local files into Blender. Supports jpg, png, avif, heic, webp, gif formats.",
    "version": (1, 0, 0),
}

import bpy
import os
import tempfile
import subprocess
import sys
from mathutils import Vector, Matrix

class InstallPillowOperator(bpy.types.Operator):
    """Install Pillow"""
    bl_idname = "preferences.install_pillow"
    bl_label = "Install Pillow"

    def execute(self, context):
        try:
            import ensurepip
            ensurepip.bootstrap()
            subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
            self.report({'INFO'}, "Pillow installed successfully. Please restart Blender.")
        except Exception as e:
            self.report({'ERROR'}, f"Failed to install Pillow: {e}")
        return {'FINISHED'}

def ensure_pillow():
    try:
        import PIL
        return True
    except ImportError:
        return False

def get_camera_facing_position(context, distance=5.0):
    """Calculate position and rotation to face the camera"""
    scene = context.scene
    camera = scene.camera
    
    if not camera:
        # If no camera, place at origin facing forward
        return Vector((0, 0, 0)), (0, 0, 0)
    
    # Get camera matrix
    camera_matrix = camera.matrix_world
    
    # Calculate forward direction (camera looks down negative Z)
    forward_vector = camera_matrix.to_3x3() @ Vector((0, 0, -1))
    forward = forward_vector.normalized()
    
    # Calculate position in front of camera
    camera_location = camera_matrix.translation
    position = camera_location + forward * distance
    
    # Calculate rotation to face camera
    # Create a rotation matrix that faces the camera
    direction = (camera_location - position).normalized()
    
    # Create rotation matrix
    if abs(direction.z) < 0.999:
        up = Vector((0, 0, 1))
        right = direction.cross(up).normalized()
        up = right.cross(direction).normalized()
    else:
        right = Vector((1, 0, 0))
        up = Vector((0, 1, 0))
    
    rotation_matrix = Matrix((
        right,
        up,
        -direction
    )).transposed()
    
    rotation = rotation_matrix.to_euler()
    
    return position, rotation

def get_viewport_facing_position(context, distance=5.0):
    """Calculate position in front of the user's viewport view"""
    # Get the 3D viewport region
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            for region in area.regions:
                if region.type == 'WINDOW':
                    # Get viewport view matrix
                    rv3d = area.spaces[0].region_3d
                    view_matrix = rv3d.view_matrix
                    
                    # Get view location and direction
                    view_location = view_matrix.inverted().translation
                    view_rotation = view_matrix.inverted().to_euler()
                    
                    # Calculate forward direction from viewport
                    forward = view_matrix.inverted().to_3x3() @ Vector((0, 0, -1))
                    forward = forward.normalized()
                    
                    # Position in front of viewport
                    position = view_location + forward * distance
                    
                    return position, view_rotation
    
    # Fallback to origin if no viewport found
    return Vector((0, 0, 0)), (0, 0, 0)

class PastePureRefImageOperator(bpy.types.Operator):
    """Paste Image from Clipboard"""
    bl_idname = "image.paste_pureref_image"
    bl_label = "Paste PureRef Image"
    bl_icon = 'IMAGE_DATA'

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D'

    def execute(self, context):
        try:
            from PIL import ImageGrab, Image
            image = ImageGrab.grabclipboard()
            if isinstance(image, Image.Image):
                temp_dir = tempfile.gettempdir()
                temp_path = os.path.join(temp_dir, "clipboard_image.png")
                image.save(temp_path)
                
                # Load image and create empty object (не используем import_image.to_plane)
                img = bpy.data.images.load(temp_path)
                
                ref = bpy.data.objects.new(name=img.name, object_data=None)
                ref.empty_display_type = 'IMAGE'
                ref.data = img
                
                # Position in front of user's viewport view
                position, rotation = get_viewport_facing_position(context, distance=5.0)
                ref.location = position
                ref.rotation_euler = rotation
                
                # Scale uniformly to preserve aspect ratio
                base_scale = 2.0  # Base size
                ref.scale = (base_scale, base_scale, 1.0)  # Uniform scaling
                
                context.collection.objects.link(ref)
                
                # Select the new object
                bpy.context.view_layer.objects.active = ref
                ref.select_set(True)
                
                self.report({'INFO'}, "Image pasted from clipboard and positioned in front of viewport")
                    
            else:
                self.report({'WARNING'}, "No image in clipboard")
        except ImportError:
            self.report({'ERROR'}, "Pillow is not installed. Please install Pillow from the add-on preferences and restart Blender.")
        except Exception as e:
            self.report({'ERROR'}, str(e))
        
        return {'FINISHED'}

class PastePureRefFromCursorOperator(bpy.types.Operator):
    """Paste Image from Clipboard at Cursor"""
    bl_idname = "image.paste_pureref_from_cursor"
    bl_label = "Paste PureRef from Cursor"
    bl_icon = 'IMAGE_DATA'

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D'

    def execute(self, context):
        try:
            from PIL import ImageGrab, Image
            image = ImageGrab.grabclipboard()
            if isinstance(image, Image.Image):
                temp_dir = tempfile.gettempdir()
                temp_path = os.path.join(temp_dir, "clipboard_image.png")
                image.save(temp_path)
                
                # Load image and create empty object
                img = bpy.data.images.load(temp_path)
                
                ref = bpy.data.objects.new(name=img.name, object_data=None)
                ref.empty_display_type = 'IMAGE'
                ref.data = img
                
                # Позиция 3D курсора
                cursor_location = context.scene.cursor.location
                ref.location = cursor_location
                
                # Используем ту же логику поворота к пользователю, что и в первой кнопке
                _, rotation = get_viewport_facing_position(context, distance=0.0)
                ref.rotation_euler = rotation
                
                # Uniform scaling to preserve aspect ratio
                base_scale = 2.0
                ref.scale = (base_scale, base_scale, 1.0)
                
                context.collection.objects.link(ref)
                
                # Select the new object
                bpy.context.view_layer.objects.active = ref
                ref.select_set(True)
                
                self.report({'INFO'}, "Image pasted from clipboard at cursor position facing user")
                    
            else:
                self.report({'WARNING'}, "No image in clipboard")
        except ImportError:
            self.report({'ERROR'}, "Pillow is not installed. Please install Pillow from the add-on preferences and restart Blender.")
        except Exception as e:
            self.report({'ERROR'}, str(e))
        
        return {'FINISHED'}

class PasterefPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    def draw(self, context):
        layout = self.layout
        if not ensure_pillow():
            layout.operator(InstallPillowOperator.bl_idname, text="Install Pillow")
            layout.label(text="Please restart Blender after installation.", icon='INFO')

def menu_func(self, context):
    self.layout.operator(PastePureRefImageOperator.bl_idname, icon='IMAGE_DATA')
    self.layout.operator(PastePureRefFromCursorOperator.bl_idname, icon='IMAGE_DATA')

def register():
    bpy.utils.register_class(InstallPillowOperator)
    bpy.utils.register_class(PastePureRefImageOperator)
    bpy.utils.register_class(PastePureRefFromCursorOperator)
    bpy.utils.register_class(PasterefPreferences)
    bpy.types.VIEW3D_MT_add.append(menu_func)

def unregister():
    bpy.utils.unregister_class(InstallPillowOperator)
    bpy.utils.unregister_class(PastePureRefImageOperator)
    bpy.utils.unregister_class(PastePureRefFromCursorOperator)
    bpy.utils.unregister_class(PasterefPreferences)
    bpy.types.VIEW3D_MT_add.remove(menu_func)

if __name__ == "__main__":
    register()

