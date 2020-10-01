import numpy as np
import PIL
from PIL import Image

# -----------------------------------------------------------------------------
# Read in the images
# -----------------------------------------------------------------------------
list_im = ['CASY_2020_09_19.jpg', 'CASY_Analysis_2020_10_01.jpg']
imgs    = [ PIL.Image.open(i) for i in list_im ]
print ("The Original image list is ", imgs)
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# pick the image which is the smallest, and resize the others to match
# it (can be arbitrary image shape here)
# -----------------------------------------------------------------------------
# max_shape = sorted( [(np.sum(i.size), i.size ) for i in imgs],reverse=True)[0][1]
min_shape = sorted([(np.sum(i.size), i.size ) for i in imgs])[0][1]
resize_imgs_list = [i.resize(min_shape) for i in imgs ]
print ("The min shape (LxW) is", min_shape, " and the type is ", type(min_shape))
print ("The resized image list is ", resize_imgs_list)
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Horizontal  and vertical stack
# -----------------------------------------------------------------------------
imgs_hstack_comb = np.hstack(resize_imgs_list)
imgs_hstack_comb = PIL.Image.fromarray( imgs_hstack_comb)
imgs_hstack_comb.save( 'Combined_horizontal_stack.jpg' )

imgs_vstack_comb = np.vstack(resize_imgs_list)
imgs_vstack_comb = PIL.Image.fromarray( imgs_vstack_comb)
imgs_vstack_comb.show()
imgs_vstack_comb.save( 'Combined_vertical_stack.jpg' )
# -----------------------------------------------------------------------------
