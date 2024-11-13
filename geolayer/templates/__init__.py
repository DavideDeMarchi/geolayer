from geolayer.utility.templates import load_mask

RGB_MASK = load_mask(mask_name='rgb')

# from geolayer.utility.mask import fill_mask
#
# print(fill_mask(RGB_MASK, band=3))
# print(RGB_MASK)


# format_string = "Name: {name}, Age: {age}, Height: {height:.2f}, ID: {id}"
#
# print(format_string.format(name='edo', age='edo', height=10,  id =121))