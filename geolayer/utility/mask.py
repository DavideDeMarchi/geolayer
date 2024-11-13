import inspect
import os

MASKS_PATH = os.path.join(os.path.dirname(__file__), '../masks')


def load_mask(mask_name):
    with open(os.path.join(MASKS_PATH, '{}.xml'.format(mask_name)), 'r') as f:
        return f.read()


def fill_mask(mask_str, **kwargs):
    return mask_str.format(**kwargs)

# MM = read_mask(mask_name='rgb')
# print(fill_mask(MM, band=4))

# print('%s' % 2333)
#
# name = "Alice"
# age = 25
# height = 5.6
