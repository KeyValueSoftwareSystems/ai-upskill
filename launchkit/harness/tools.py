from launchkit.harness.trace import Trace


def make_generate_image(images, colours: dict, trace: Trace):
    def generate_image(image_prompt: str) -> dict:
        """Make the poster picture from a description of the scene. The picture contains no words."""
        # TODO step 3: call images.generate(image_prompt, colours) and return {"file": path}
        return {"status": "not built", "reason": "the image tool is step 3"}

    return generate_image
