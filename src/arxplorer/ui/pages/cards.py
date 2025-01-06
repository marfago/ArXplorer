import json
import textwrap
from datetime import datetime

import dash
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
from dash import dcc
from dash import html, callback, Input, Output, State, no_update
from dash.exceptions import PreventUpdate

from arxplorer.persitence.database import DbOperations

dash.register_page(__name__, path="/")


def layout():
    return html.Div([html.H3("Queries"), html.Div(id="query-list")])


@callback(
    Output("query-list", "children"),
    Input("url", "pathname"),
    Input("auto-refresh-interval", "n_intervals"),
    Input("refresh-trigger", "data"),
    Input({"type": "refresh-trigger", "index": dash.ALL}, "data"),
    Input("manual-refresh", "n_clicks"),
)
def display_query_cards(pathname, n_intervals, global_refresh, individual_refreshes, manual_refresh):
    # ctx = dash.callback_context
    # if not ctx.triggered:
    #    raise PreventUpdate

    if pathname == "/":
        queries = DbOperations.get_queries()
        cards = [create_query_card(query) for query in queries]
        return dbc.Row(
            [dbc.Col(card, width=4, className="mb-4") for card in cards],
            className="row-eq-height",
        )
    return no_update


def create_query_card(query):
    query_stats = DbOperations.get_query_stats(query["query_id"])

    if query["status"].lower() == "running":
        status_class = "status-running"
    elif query["status"].lower() == "to_delete":
        status_class = "status-to-delete"
    else:
        status_class = "status-stopped"

    last_updated = datetime.fromisoformat(query_stats["query_last_updated_at"])
    last_updated_str = f"Last updated {last_updated.strftime('%Y-%m-%d %H:%M:%S')}"

    # Calculate the best score and prepare data for histogram
    scores = query_stats["papers_by_relevance_score"]
    best_score = max(scores.keys()) if scores else 0

    # Create histogram
    histogram = go.Figure(
        data=[
            go.Bar(
                x=list(scores.keys()),
                y=list(scores.values()),
                texttemplate="%{y}",
                textfont_size=10,
                marker_color="rgba(0, 123, 255, 0.6)",
            )
        ]
    )
    histogram.update_layout(
        title=None,
        xaxis_title=None,
        yaxis_title=None,
        margin=dict(l=5, r=5, t=5, b=5),
        height=150,
        width=200,
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(size=10, color="black"),
        showlegend=False,
    )
    histogram.update_xaxes(overwrite=True, showticklabels=True, showgrid=False, zeroline=False)
    histogram.update_yaxes(showticklabels=False, showgrid=False, zeroline=False)

    toggle_btn_class = "toggle-query-btn running" if query["status"].lower() == "running" else "toggle-query-btn"
    card_class = "h-100 clickable-card" + (" disabled" if query["status"].lower() == "to_delete" else "")

    truncated_text = textwrap.shorten(query["query_text"], width=400, placeholder="...")

    card_content = dbc.CardBody(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Div(
                                truncated_text,
                                id={"type": "query-text", "index": query["query_id"]},
                                className="mb-2 query-text",
                                title=query["query_text"],  # This will create a native HTML tooltip
                            ),
                        ],
                        width=True,
                    ),
                ],
                align="start",
                className="g-0",
            ),
            html.Div(className="flex-grow-1"),
            html.Div(
                [
                    html.P(last_updated_str, className="card-subtitle mb-2 text-right"),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Span(
                                        query_stats["total_papers"],
                                        className="stat-value",
                                    ),
                                    html.Span("Total Papers", className="stat-label"),
                                ],
                                className="stat-item",
                            ),
                            html.Div(
                                [
                                    dbc.Tooltip(
                                        dcc.Graph(
                                            figure=histogram,
                                            config={"displayModeBar": False},
                                        ),
                                        target=f"best-score-{query['query_id']}",
                                        placement="top",
                                    ),
                                    html.Span(
                                        f"{best_score:.0f}",
                                        id=f"best-score-{query['query_id']}",
                                        className="stat-value",
                                    ),
                                    html.Span("Best Score", className="stat-label"),
                                ],
                                className="stat-item",
                            ),
                            html.Div(
                                [
                                    html.Span(f"{len(scores)}", className="stat-value"),
                                    html.Span("Unique Scores", className="stat-label"),
                                ],
                                className="stat-item",
                            ),
                        ],
                        className="card-stats",
                    ),
                ],
                className="card-footer",
            ),
        ],
        className="d-flex flex-column h-100",
    )

    return dbc.Card(
        [
            dbc.Row(
                [
                    dbc.Col(
                        html.Div(className=f"status-indicator {status_class}"),
                        width="auto",
                        style={"padding": "10px 0px 0px 10px"},
                    ),
                    dbc.Col([], width=True),
                    dbc.Col(
                        [
                            dbc.Button(
                                html.I(className=f"fas fa-{'stop' if query['status'].lower() == 'running' else 'play'}"),
                                id={"type": "toggle-query", "index": query["query_id"]},
                                className=toggle_btn_class,
                                n_clicks=0,
                                disabled=query["status"].lower() == "to_delete",
                            ),
                            dbc.Button(
                                html.I(className="fas fa-trash"),
                                id={"type": "delete-query", "index": query["query_id"]},
                                className="delete-query-btn",
                                n_clicks=0,
                                disabled=query["status"].lower() == "to_delete",
                            ),
                        ],
                        width="auto",
                        style={"padding": "10px 0px 0px 10px"},
                    ),
                ],
                align="start",
                className="g-0",
            ),
            dcc.Store(id={"type": "refresh-trigger", "index": query["query_id"]}, data=0),
            dcc.Link(
                card_content,
                href=f"/papers?query_id={query['query_id']}",
                style={"textDecoration": "none", "color": "inherit"},
                className=card_class,
            ),
        ],
        className=card_class,
    )


@callback(
    Output({"type": "toggle-query", "index": dash.MATCH}, "children"),
    Output({"type": "toggle-query", "index": dash.MATCH}, "className"),
    Output({"type": "refresh-trigger", "index": dash.MATCH}, "data"),
    Input({"type": "toggle-query", "index": dash.ALL}, "n_clicks"),
    State({"type": "toggle-query", "index": dash.ALL}, "id"),
    prevent_initial_call=True,
)
def toggle_query(n_clicks, ids):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate

    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    query_id = json.loads(button_id)["index"]

    query = DbOperations.get_query(query_id)
    if query["status"].lower() == "running":
        DbOperations.set_stop_query(query_id)
        new_icon = html.I(className="fas fa-play")
        new_class = "toggle-query-btn"
    else:
        DbOperations.set_running_query(query_id)
        new_icon = html.I(className="fas fa-stop")
        new_class = "toggle-query-btn running"

    return new_icon, new_class, query_id  # Return query_id to trigger refresh


@callback(
    Output("delete-modal", "is_open"),
    Output("query-to-delete", "data"),
    Input({"type": "delete-query", "index": dash.ALL}, "n_clicks"),
    Input("cancel-delete", "n_clicks"),
    Input("confirm-delete", "n_clicks"),
    State("delete-modal", "is_open"),
    prevent_initial_call=True,
)
def toggle_modal(delete_clicks, cancel_clicks, confirm_clicks, is_open):
    ctx = dash.callback_context

    if not ctx.triggered:
        return no_update, no_update

    trigger = ctx.triggered[0]
    prop_id = trigger["prop_id"]

    if prop_id == "cancel-delete.n_clicks" or prop_id == "confirm-delete.n_clicks":
        return False, None

    if "delete-query" in prop_id:
        button_id = json.loads(prop_id.split(".")[0])
        if trigger["value"]:
            return True, button_id["index"]

    return no_update, no_update


@callback(
    Output({"type": "refresh-trigger", "index": dash.MATCH}, "data", allow_duplicate=True),
    Input("confirm-delete", "n_clicks"),
    State("query-to-delete", "data"),
    prevent_initial_call=True,
)
def delete_query(confirm_clicks, query_id):
    if confirm_clicks and query_id:
        DbOperations.set_to_delete_query(query_id)
        return query_id
    return dash.no_update


@callback(
    Output("new-query-modal", "is_open", allow_duplicate=True),
    Output("new-query-input", "value"),
    Input("new-query", "n_clicks"),
    Input("cancel-new-query", "n_clicks"),
    Input("submit-new-query", "n_clicks"),
    State("new-query-modal", "is_open"),
    State("new-query-input", "value"),
    prevent_initial_call=True,
)
def toggle_new_query_modal(new_query_clicks, cancel_clicks, submit_clicks, is_open, current_value):
    ctx = dash.callback_context
    if not ctx.triggered:
        return no_update, no_update

    button_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if button_id == "new-query":
        return not is_open, ""
    elif button_id == "cancel-new-query":
        return False, current_value
    elif button_id == "submit-new-query":
        return False, current_value

    return no_update, no_update


@callback(
    Output("refresh-trigger", "data"),
    Input("submit-new-query", "n_clicks"),
    State("new-query-input", "value"),
    prevent_initial_call=True,
)
def submit_new_query(submit_clicks, query_text):
    if submit_clicks and query_text:
        new_query_id = DbOperations.add_query(query_text)
        return new_query_id
    return dash.no_update
