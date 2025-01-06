import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, callback, Input, Output, State

from arxplorer.configuration import ConfigurationManager

dash.register_page(__name__, "/settings")


def create_setting_row(label, id, value, input_type="text", disabled=False):
    return dbc.Row(
        [
            dbc.Col(html.Label(label), width=4),
            dbc.Col(dbc.Input(id=id, value=value, type=input_type, disabled=disabled), width=8),
        ],
        className="mb-3",
    )


llm_model_options = {
    "gemini/gemini-2.0-flash": "Gemini 2.0 Flash",
    "gemini/gemini-2.0-flash-lite-preview-02-05": "Gemini 2.0 Flash-Lite Preview",
    "gemini/gemini-1.5-flash": "Gemini 1.5 Flash",
    "gemini/gemini-1.5-flash-8b": "Gemini 1.5 Flash-8B",
    "gemini/gemini-1.5-pro": "Gemini 1.5 Pro",
}

retry_strategy_options = [
    {"label": "Exponential backoff", "value": "exponential_backoff_retry"},
    # Add other retry strategies here if needed
]

layout = html.Div(
    [
        dcc.Location(id="settings-url", refresh=False),
        html.Div(
            [
                dbc.Row(
                    [
                        dbc.Col(html.H1("Settings"), width=True),
                    ],
                    className="align-items-center mb-3",
                ),
            ],
            className="back-button-container",
        ),
        html.Div(
            [
                create_setting_row(
                    "Application Folder", "app-folder", ConfigurationManager.get_application_folder(), disabled=True
                ),
                dbc.Row(
                    [
                        dbc.Col(html.Label("Conversion Speed"), width=4),
                        dbc.Col(
                            dcc.Dropdown(
                                id="conversion-speed",
                                options=[
                                    {"label": "Fast - read from html if available", "value": "fast"},
                                    {"label": "Slow - read from pdf", "value": "slow"},
                                ],
                                value=ConfigurationManager.get_conversion_speed(),
                            ),
                            width=8,
                        ),
                    ],
                    className="mb-3",
                ),
                create_setting_row(
                    "Max Parallel Tasks", "max-parallel-tasks", ConfigurationManager.get_max_parallel_tasks(), "number"
                ),
                create_setting_row(
                    "Max Parallel Convert Processes",
                    "max-parallel-convert",
                    ConfigurationManager.get_max_parallel_convert_processes(),
                    "number",
                ),
                create_setting_row(
                    "Max Queries Per Minute",
                    "max-queries-per-minute",
                    ConfigurationManager.get_max_queries_per_minute(),
                    "number",
                ),
                dbc.Row(
                    [
                        dbc.Col(html.Label("LLM Model"), width=4),
                        dbc.Col(
                            dcc.Dropdown(
                                id="llm-model",
                                options=[{"label": v, "value": k} for k, v in llm_model_options.items()],
                                value=ConfigurationManager.get_llm_model(),
                                clearable=False,
                            ),
                            width=8,
                        ),
                    ],
                    className="mb-3",
                ),
                dbc.Row(
                    [
                        dbc.Col(html.Label("LLM Client Retry Strategy"), width=4),
                        dbc.Col(
                            dcc.Dropdown(
                                id="llm-retry-strategy",
                                options=retry_strategy_options,
                                value=ConfigurationManager.get_llm_client_retry_strategy(),
                                clearable=False,
                            ),
                            width=8,
                        ),
                    ],
                    className="mb-3",
                ),
                create_setting_row(
                    "LLM Client Max Retries", "llm-max-retries", ConfigurationManager.get_llm_client_max_num_retries(), "number"
                ),
                dbc.Row(
                    [
                        dbc.Col(html.Label("Google API Key"), width=4),
                        dbc.Col(
                            [
                                html.Span(
                                    "Available" if ConfigurationManager.is_google_gemini_key_available() else "Not Available"
                                ),
                                html.I(
                                    className=(
                                        "fas fa-check-circle text-success ms-2"
                                        if ConfigurationManager.is_google_gemini_key_available()
                                        else "fas fa-times-circle text-danger ms-2"
                                    )
                                ),
                            ],
                            width=8,
                        ),
                    ],
                    className="mb-3",
                ),
                dbc.Button(
                    [html.I(className="fas fa-save me-2"), "Save Settings"],
                    id="save-settings",
                    color="primary",
                    className="custom-button mt-3",
                ),
            ]
        ),
        dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle("Settings Saved")),
                dbc.ModalBody("Your settings have been updated successfully.\nRestart the application to apply them."),
                dbc.ModalFooter(dbc.Button("Close", id="close-modal", className="ms-auto", n_clicks=0)),
            ],
            id="success-modal",
            is_open=False,
        ),
    ]
)


@callback(
    [Output("success-modal", "is_open"), Output("settings-url", "pathname")]
    + [
        Output(setting, "value")
        for setting in [
            "conversion-speed",
            "max-parallel-tasks",
            "max-parallel-convert",
            "max-queries-per-minute",
            "llm-model",
            "llm-retry-strategy",
            "llm-max-retries",
        ]
    ],
    [Input("save-settings", "n_clicks"), Input("close-modal", "n_clicks")],
    [
        State(setting, "value")
        for setting in [
            "conversion-speed",
            "max-parallel-tasks",
            "max-parallel-convert",
            "max-queries-per-minute",
            "llm-model",
            "llm-retry-strategy",
            "llm-max-retries",
        ]
    ],
)
def save_settings(
    save_clicks,
    close_clicks,
    conversion_speed,
    max_parallel_tasks,
    max_parallel_convert,
    max_queries_per_minute,
    llm_model,
    llm_retry_strategy,
    llm_max_retries,
):
    ctx = dash.callback_context
    if not ctx.triggered:
        return False, dash.no_update, *[dash.no_update] * 7

    button_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if button_id == "save-settings":
        ConfigurationManager.update_config("conversion_speed", conversion_speed)
        ConfigurationManager.update_config("max_parallel_tasks", int(max_parallel_tasks))
        ConfigurationManager.update_config("max_parallel_convert_processes", int(max_parallel_convert))
        ConfigurationManager.update_config("max_queries_per_minute", int(max_queries_per_minute))
        ConfigurationManager.update_config("llm_model", llm_model)
        ConfigurationManager.update_config("llm_client_retry_strategy", llm_retry_strategy)
        ConfigurationManager.update_config("llm_client_max_num_retries", int(llm_max_retries))
        return True, "/", *[dash.no_update] * 7
    elif button_id == "close-modal":
        return False, "/", *[dash.no_update] * 7

    return False, dash.no_update, *[dash.no_update] * 7
