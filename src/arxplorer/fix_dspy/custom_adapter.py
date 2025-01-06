import litellm
from dspy import JSONAdapter


class CustomJSONAdapter(JSONAdapter):
    """
    This class is needed to fix a bug with the original JSONAdapter and Gemini
    It seems like Gemini does not understand DSPyProgramOutputs and require a json_object instead
    """

    def __call__(self, lm, lm_kwargs, signature, demos, inputs, _parse_values=True):
        inputs = self.format(signature, demos, inputs)
        inputs = dict(prompt=inputs) if isinstance(inputs, str) else dict(messages=inputs)

        try:
            provider = lm.model.split("/", 1)[0] or "openai"
            if "response_format" in litellm.get_supported_openai_params(model=lm.model, custom_llm_provider=provider):
                outputs = lm(**inputs, **lm_kwargs, response_format={"type": "json_object"})
            else:
                outputs = lm(**inputs, **lm_kwargs)

        except litellm.UnsupportedParamsError:
            outputs = lm(**inputs, **lm_kwargs)

        values = []

        for output in outputs:
            value = self.parse(signature, output, _parse_values=_parse_values)
            assert set(value.keys()) == set(
                signature.output_fields.keys()
            ), f"Expected {signature.output_fields.keys()} but got {value.keys()}"
            values.append(value)

        return values
