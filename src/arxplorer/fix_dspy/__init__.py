def update_dsp_lm_call(max_tokens: int = 15, time_in_seconds: float = 60):
    import dspy
    from arxplorer.common.limiter import RateLimiter

    RL = RateLimiter(max_tokens, time_in_seconds)
    litellm_completion_orig = dspy.clients.lm.litellm_completion

    def litellm_completion_new(*args, **kwargs):
        RL.get_token()
        return litellm_completion_orig(*args, **kwargs)

    dspy.clients.lm.litellm_completion = litellm_completion_new
