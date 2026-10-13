from launchkit.harness.run import run_request


def test_endless_fake_stops_at_the_step_cap(settings, images, trace, request_for, endless):
    """The endless fake stops at the step cap."""
    run_request(request_for(), settings=settings, model=endless, images=images, trace=trace)
    assert len(trace.tool_calls("generate_image")) == settings.limits.step_cap
    assert any(e.kind == "stop" and "step cap" in e.detail["reason"] for e in trace.events)


def test_fourth_image_call_is_refused(settings, images, trace, request_for, endless):
    """A 4th image call against a budget of 3 is refused."""
    run_request(request_for(), settings=settings, model=endless, images=images, trace=trace)
    assert len(images.calls) == settings.limits.image_budget
    refused = [e for e in trace.events if e.kind == "refused"]
    assert len(refused) == settings.limits.step_cap - settings.limits.image_budget


def test_image_prompt_has_no_headline(settings, images, trace, request_for, good):
    """The image prompt sent to the adapter never contains the headline."""
    result = run_request(request_for(), settings=settings, model=good, images=images, trace=trace)
    assert result.image is not None
    assert images.calls
    assert all(result.spec.headline.lower() not in prompt.lower() for prompt, _ in images.calls)
