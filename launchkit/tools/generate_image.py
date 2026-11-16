"""generate_image: draws the poster picture with the image model. In a conversation it saves into the outputs/ drawer
and records what it wrote, under its own name. Reference page 11, Recording what the agent produced.
"""

from launchkit.files.record import record
from launchkit.trace import Trace


def make_generate_image(images, colours: dict, trace: Trace, on_made=None, files=None, message: str = ""):
    def generate_image(image_prompt: str) -> dict:
        """Make the poster picture from a description of the scene. The picture contains no words."""
        path = images.generate(image_prompt, colours)
        if on_made is not None:
            on_made(path)
        if files is not None:
            record(files.root, path.relative_to(files.root), "generate_image", message)
        return {"file": str(path)}

    return generate_image
