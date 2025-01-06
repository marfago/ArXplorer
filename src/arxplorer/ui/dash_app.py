import dash
import dash_bootstrap_components as dbc
from dash import Dash, html, dcc, Input, Output, State, callback

app = Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME],
)

app.clientside_callback(
    """
    function(n_clicks) {
        document.addEventListener('click', function(e) {
            if (e.target.closest('[data-stop-propagation]')) {
                e.stopPropagation();
            }
        }, true);
        return '';
    }
    """,
    Output("dummy-div", "children"),
    Input("dummy-div", "children"),
)

app.layout = html.Div(
    [
        dcc.Location(id="url", refresh=False),
        dcc.Store(id="auto-refresh-store", storage_type="local", data="false"),
        dcc.Store(id="theme-store", storage_type="local", data="light-theme"),
        dcc.Store(id="query-to-delete", storage_type="memory"),
        dcc.Store(id="refresh-trigger", storage_type="memory"),
        dcc.Store(id="global-loading-trigger", data={"is_loading": False}),
        dcc.Interval(id="auto-refresh-interval", interval=15_000, n_intervals=0, disabled=False),
        html.Div(id="dummy-div", style={"display": "none"}),
        # Sidebar
        html.Div(
            [
                html.Div([html.I(className="fas fa-robot")], className="logo"),
                html.Div(
                    [
                        dbc.Nav(
                            [
                                dbc.NavLink(
                                    [
                                        html.I(className="fas fa-search"),
                                        html.Span("Queries"),
                                    ],
                                    href="/",
                                    id="projects-link",
                                ),
                            ],
                            vertical=True,
                            pills=True,
                            className="mb-auto",
                        ),
                        dbc.Nav(
                            [
                                dbc.NavLink(
                                    [
                                        html.I(className="fas fa-cog"),
                                        html.Span("Settings"),
                                    ],
                                    href="/settings",
                                    id="settings-link",
                                ),
                                dbc.NavLink(
                                    [
                                        html.I(className="fas fa-book"),
                                        html.Span("Documentation"),
                                    ],
                                    href="#",
                                    id="docs-link",
                                ),
                                dbc.NavLink(
                                    [
                                        html.I(className="fas fa-question-circle"),
                                        html.Span("Support"),
                                    ],
                                    href="#",
                                    id="support-link",
                                ),
                                dbc.NavLink(
                                    [
                                        html.I(className="fas fa-adjust"),
                                        html.Span("Dark"),
                                    ],
                                    href="#",
                                    id="theme-toggle",
                                ),
                            ],
                            vertical=True,
                            pills=True,
                        ),
                    ],
                    className="sidebar-content",
                ),
            ],
            className="sidebar",
        ),
        # Main content
        html.Div(
            [
                dcc.Loading(
                    id="loading-page-content",
                    overlay_style={"visibility": "visible", "filter": "blur(0px)"},
                    children=[
                        # Banner
                        html.Div(
                            [
                                html.H1("ArXplorer", className="banner-title"),
                                html.Div(
                                    [
                                        html.Div(
                                            [
                                                dbc.Button(
                                                    id="manual-refresh",
                                                    className="custom-button me-2",
                                                    children=[
                                                        html.I(className="fas fa-sync-alt me-2"),
                                                        "Refresh",
                                                    ],
                                                    color="primary",
                                                ),
                                                dbc.Button(
                                                    id="auto-refresh",
                                                    className="custom-toggle-button me-2",
                                                    children=[
                                                        html.Span(
                                                            "Auto-Refresh",
                                                            className="toggle-label",
                                                        ),
                                                        html.Div(className="toggle-switch"),
                                                    ],
                                                ),
                                            ],
                                            className="auto-refresh-container",
                                        ),
                                        dbc.Button(
                                            [
                                                html.I(className="fas fa-plus me-2"),
                                                "New Query",
                                            ],
                                            id="new-query",
                                            color="primary",
                                            className="custom-button",
                                        ),
                                    ],
                                    className="banner-controls",
                                ),
                            ],
                            id="banner",
                            className="banner",
                        ),
                        # Page content
                        html.Div([dash.page_container], id="page-content", className="content"),
                        # Modals
                        # Wrap modals in a themed container
                        dbc.Modal(
                            [
                                dbc.ModalHeader(dbc.ModalTitle("Delete Query")),
                                dbc.ModalBody("Are you sure you want to delete this query? This action cannot be undone."),
                                dbc.ModalFooter(
                                    [
                                        dbc.Button("Cancel", id="cancel-delete", className="me-1"),
                                        dbc.Button("Delete", id="confirm-delete", color="danger"),
                                    ]
                                ),
                            ],
                            id="delete-modal",
                            is_open=False,
                        ),
                        dbc.Modal(
                            [
                                dbc.ModalHeader(dbc.ModalTitle("New Query")),
                                dbc.ModalBody(
                                    [
                                        dcc.Textarea(
                                            id="new-query-input",
                                            placeholder="Enter your query",
                                            style={
                                                "width": "100%",
                                                "height": "150px",
                                                "resize": "vertical",
                                            },
                                        ),
                                    ]
                                ),
                                dbc.ModalFooter(
                                    [
                                        dbc.Button(
                                            "Cancel",
                                            id="cancel-new-query",
                                            className="me-1",
                                        ),
                                        dbc.Button(
                                            "Submit",
                                            id="submit-new-query",
                                            color="primary",
                                        ),
                                    ]
                                ),
                            ],
                            id="new-query-modal",
                            is_open=False,
                        ),
                    ],
                ),
            ],
            className="main-content",
        ),
    ],
    id="main-container",
    className="light-theme",
)


@callback(
    Output("auto-refresh", "className"),
    Output("auto-refresh-store", "data"),
    Output("auto-refresh-interval", "disabled"),
    Input("auto-refresh", "n_clicks"),
    State("auto-refresh", "className"),
    State("auto-refresh-store", "data"),
)
def toggle_auto_refresh(n_clicks, current_class, stored_value):
    if n_clicks is None:
        # Initial load
        is_active = stored_value == "true"
    else:
        # Button was clicked
        is_active = "active" not in current_class

    new_class = "custom-toggle-button active" if is_active else "custom-toggle-button"
    return new_class, str(is_active).lower(), not is_active


@callback(
    Output("main-container", "className"),
    Output("delete-modal", "className"),
    Output("new-query-modal", "className"),
    Output("theme-toggle", "children"),
    Output("theme-store", "data"),
    Input("theme-toggle", "n_clicks"),
    State("main-container", "className"),
    State("theme-store", "data"),
)
def toggle_theme(n_clicks, current_theme, stored_theme):
    if n_clicks is None:
        # On initial load, use the stored theme
        return stored_theme, stored_theme, stored_theme, dash.no_update, stored_theme
    if current_theme == "light-theme":
        new_theme = "dark-theme"
        new_text = [html.I(className="fas fa-adjust"), html.Span("Light")]
    else:
        new_theme = "light-theme"
        new_text = [html.I(className="fas fa-adjust"), html.Span("Dark")]
    return new_theme, new_theme, new_theme, new_text, new_theme


@callback(
    Output("main-container", "className", allow_duplicate=True),
    Output("delete-modal", "className", allow_duplicate=True),
    Output("new-query-modal", "className", allow_duplicate=True),
    Input("theme-store", "data"),
    prevent_initial_call="initial_duplicate",
)
def set_initial_theme(stored_theme):
    theme = stored_theme or "light-theme"
    return theme, theme, theme


@callback(
    Output("new-query-modal", "is_open"),
    Input("new-query", "n_clicks"),
    State("new-query-modal", "is_open"),
    prevent_initial_call=True,
)
def open_new_query_modal(n_clicks, is_open):
    if n_clicks:
        return not is_open
    return is_open


if __name__ == "__main__":
    app.run_server(debug=True)
