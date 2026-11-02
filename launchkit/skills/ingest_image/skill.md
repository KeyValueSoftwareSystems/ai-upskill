# ingest_image

Pick me when: the marketer gives a photo, e.g. "use our shoot photo", and wants it used for the poster.
Uses: describe_image, detect_focal_point, crop, expand_canvas

## Steps

1. Call describe_image.
2. If the photo shows any words or another brand's logo, stop and tell the marketer what you saw.
3. Otherwise the photo is now the picture to work on: call detect_focal_point to find the product in it.
4. Then do the sizes the way the resize_image skill says: crop with only width and height, and expand_canvas when crop says the product does not fit.
5. Reply with the sizes you made. The photo is the picture only: describe_image's words are a check, never poster copy, and the photo is never a source. If the marketer also asks for poster words, write them the way the on_brand_copy skill says.
