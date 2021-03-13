from abc import abstractmethod

import pygame as pg
import numpy as np
# from wand.image import Image



class PostprocessingEffect:
    @staticmethod
    @abstractmethod
    def apply_effect(source_surf: pg.Surface) -> pg.Surface:
        """returns a copy of the given surface with the effect applied"""
        pass


# TODO: maybe implement this ourselves with c bindings
# class BarrelDistortion(PostprocessingEffect):
#     @staticmethod
#     def apply_effect(source_surf):
#         pixels = pg.surfarray.array3d(source_surf)
#         with Image.from_array(pixels) as img:
#             img.distort('barrel', (0.1, 0.0, 0.0, 1.0))
#             new_pixels = np.array(img)
        
#         return pg.surfarray.make_surface(new_pixels)
