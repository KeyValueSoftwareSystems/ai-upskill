from launchkit.trace import Trace


def make_generate_image(images, colours: dict, trace: Trace, on_made=None):
    def generate_image(image_prompt: str) -> dict:
        """Make the poster picture from a description of the scene. The picture contains no words."""
        path = images.generate(image_prompt, colours)
        if on_made is not None:
            on_made(path)
        return {"file": str(path)}

    return generate_image
