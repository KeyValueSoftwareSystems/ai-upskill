# resize_image

Pick me when: the approved poster must go out in other sizes, e.g. all the sizes.
Uses: detect_focal_point, crop, expand_canvas
Hides: crop, expand_canvas, scale, detect_focal_point (prefer_over)

## Steps

1. Take the sizes from the brand's placements.
2. Call detect_focal_point once to find the product.
3. For each size, call crop with only width and height, so it cuts around the product.
4. If crop says the product does not fit, call expand_canvas with that size and the brand's main colour.
5. Check every result says the product is whole.

Never call scale to change the shape: it squashes the product.
