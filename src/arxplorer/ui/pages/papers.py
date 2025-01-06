import json

import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, callback, Input, Output, State, ALL, MATCH
from dash.exceptions import PreventUpdate

from arxplorer.persitence.database import DbOperations

dash.register_page(__name__, path="/papers")


def layout(query_id=None):
    return html.Div(
        [
            dcc.Store(id="expanded-rows-store", storage_type="local"),
            dcc.Store(id="previous-pathname", storage_type="memory"),
            dcc.Store(id="sort-order-store", storage_type="local"),
            html.Div(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                dcc.Link(
                                    [
                                        html.I(className="fas fa-chevron-left me-2"),
                                        "Back to Queries",
                                    ],
                                    href="/",
                                    className="btn btn-primary custom-button",
                                ),
                                width="auto",
                                className="me-3",
                            ),
                            dbc.Col(
                                html.Span(id="query-text", className="mb-0"),
                                width=True,
                            ),
                        ],
                        className="align-items-start mb-3",
                    ),
                ],
                className="back-button-container",
            ),
            html.H2(id="papers-title", className="mb-4"),
            html.Div(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                dbc.Select(
                                    id="order-by",
                                    options=[
                                        {
                                            "label": "Order by Citations",
                                            "value": "citations",
                                        },
                                        {"label": "Order by Date", "value": "date"},
                                        {"label": "Order by ID", "value": "id"},
                                        {
                                            "label": "Order by Relevance",
                                            "value": "relevance",
                                        },
                                        {"label": "Order by Title", "value": "title"},
                                    ],
                                    value="relevance",
                                    className="custom-select me-2",
                                ),
                                width=2,
                            ),
                            dbc.Col(
                                dbc.ButtonGroup(
                                    [
                                        dbc.Button(
                                            html.I(className="fas fa-sort-amount-down"),
                                            id="sort-desc",
                                            n_clicks=0,
                                            active=True,
                                            color="primary",
                                            className="me-1",
                                        ),
                                        dbc.Button(
                                            html.I(className="fas fa-sort-amount-up"),
                                            id="sort-asc",
                                            n_clicks=0,
                                            color="primary",
                                        ),
                                    ],
                                    size="sm",
                                ),
                                width="auto",
                                className="me-2",
                            ),
                            dbc.Col(
                                html.Div(
                                    [
                                        html.Label("Minimum Relevance", className="me-2"),
                                        dcc.Slider(
                                            id="relevance-filter",
                                            min=0,
                                            max=5,
                                            step=1,
                                            value=4,
                                            marks={i: str(i) for i in range(6)},
                                        ),
                                    ]
                                ),
                                width=4,
                            ),
                            dbc.Col(),
                            dbc.Col(
                                html.Div(
                                    [
                                        dbc.Input(
                                            id="text-filter",
                                            type="text",
                                            placeholder="Filter by title or explanation...",
                                            className="custom-input",
                                        ),
                                        html.Div(
                                            html.I(
                                                className="fas fa-times-circle",
                                                id="clear-text-filter",
                                            ),
                                            className="clear-button",
                                        ),
                                    ],
                                    className="input-with-clear-button",
                                ),
                                width=3,
                            ),
                            dbc.Col(
                                dbc.Button(
                                    html.I(className="fab fa-github"),
                                    id="github-filter",
                                    color="light",
                                    className="github-filter-btn",
                                    size="sm",
                                ),
                                width="auto",
                                className="me-2",
                            ),
                        ],
                        className="mb-3 align-items-center",
                    ),
                ],
                className="paper-controls",
            ),
            html.Div(id="filtered-papers-list"),
            html.Div(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                html.Div(id="pagination-info", className="text-muted"),
                                width="auto",
                                className="d-flex align-items-center",
                            ),
                            dbc.Col(
                                dbc.Pagination(
                                    id="pagination",
                                    max_value=1,
                                    first_last=True,
                                    previous_next=True,
                                    size="sm",
                                ),
                                width="auto",
                                className="d-flex justify-content-center",
                            ),
                            dbc.Col(
                                dbc.Select(
                                    id="papers-per-page",
                                    options=[
                                        {"label": "25 per page", "value": "25"},
                                        {"label": "50 per page", "value": "50"},
                                    ],
                                    value="25",
                                    size="sm",
                                ),
                                width="auto",
                                className="d-flex align-items-center",
                            ),
                        ],
                        className="mt-3 mb-3 align-items-center",
                    ),
                ],
                className="pagination-container",
            ),
            html.Div(id="dummy-div", style={"display": "none"}),
        ]
    )


def filter_papers(github_filter_class, papers, relevance_filter, text_filter):
    if relevance_filter is not None:
        papers = [p for p in papers if p["relevance_score"] >= relevance_filter]
    if text_filter:
        text_filter = text_filter.lower()
        papers = [
            p
            for p in papers
            if text_filter in p["title"].lower() or text_filter in p["relevance_score_brief_explanation"].lower()
        ]
    if "active" in github_filter_class:
        papers = [p for p in papers if extract_github_links(p)]
    return papers


def sort_papers(current_sort_order, order_by, papers, triggered_input):
    if triggered_input in ["sort-desc.n_clicks", "sort-asc.n_clicks"]:
        sort_order = "desc" if triggered_input == "sort-desc.n_clicks" else "asc"
    else:
        sort_order = current_sort_order or "desc"
    if order_by == "id":
        papers.sort(key=lambda x: x["paper_id"], reverse=(sort_order == "desc"))
    elif order_by == "title":
        papers.sort(key=lambda x: x["title"].lower(), reverse=(sort_order == "desc"))
    elif order_by == "date":
        papers.sort(key=lambda x: x["published"], reverse=(sort_order == "desc"))
    elif order_by == "citations":
        papers.sort(key=lambda x: x.get("citations", 0), reverse=(sort_order == "desc"))
    else:
        papers.sort(key=lambda x: x["relevance_score"], reverse=(sort_order == "desc"))
    return sort_order


@callback(
    Output("filtered-papers-list", "children"),
    Output("papers-title", "children"),
    Output("expanded-rows-store", "data"),
    Output("previous-pathname", "data"),
    Output("sort-desc", "active"),
    Output("sort-asc", "active"),
    Output("sort-order-store", "data"),
    Output("pagination", "max_value"),
    Output("pagination-info", "children"),
    Input("order-by", "value"),
    Input("sort-desc", "n_clicks"),
    Input("sort-asc", "n_clicks"),
    Input("relevance-filter", "value"),
    Input("text-filter", "value"),
    Input("github-filter", "className"),
    Input("url", "search"),
    Input("url", "pathname"),
    Input("auto-refresh-interval", "n_intervals"),
    Input({"type": "paper-collapse", "index": ALL}, "is_open"),
    Input("manual-refresh", "n_clicks"),
    Input("pagination", "active_page"),
    Input("papers-per-page", "value"),
    State({"type": "paper-row", "index": ALL}, "id"),
    State("expanded-rows-store", "data"),
    State("previous-pathname", "data"),
    State("sort-order-store", "data"),
)
def update_papers_list(
    order_by,
    sort_desc_clicks,
    sort_asc_clicks,
    relevance_filter,
    text_filter,
    github_filter_class,
    search,
    pathname,
    n_intervals,
    collapse_states,
    manual_refresh,
    active_page,
    papers_per_page,
    row_ids,
    expanded_rows,
    previous_pathname,
    current_sort_order,
):
    ctx = dash.callback_context
    triggered_input = ctx.triggered[0]["prop_id"] if ctx.triggered else None

    if expanded_rows is None or (previous_pathname is None and pathname == "/papers"):
        expanded_rows = {}
    else:
        expanded_rows = json.loads(expanded_rows)

    if "paper-collapse" in str(triggered_input):
        for is_open, id_dict in zip(collapse_states, row_ids):
            expanded_rows[id_dict["index"]] = is_open

    query_id = search.split("=")[-1]
    papers = DbOperations.get_papers(query_id)

    papers = filter_papers(github_filter_class, papers, relevance_filter, text_filter)

    sort_order = sort_papers(current_sort_order, order_by, papers, triggered_input)

    # Pagination
    papers_per_page = int(papers_per_page)
    total_papers = len(papers)
    total_pages = -(-total_papers // papers_per_page)
    active_page = active_page or 1
    start_idx = (active_page - 1) * papers_per_page
    end_idx = min(start_idx + papers_per_page, total_papers)
    papers_to_display = papers[start_idx:end_idx]

    papers_list = dbc.ListGroup(
        [create_paper_item(paper, expanded_rows.get(paper["paper_id"], False)) for paper in papers_to_display]
    )
    title = f"Papers ({total_papers})"

    pagination_info = f"Showing {start_idx + 1}-{end_idx} of {total_papers} papers"

    sort_desc_active = sort_order == "desc"
    sort_asc_active = sort_order == "asc"

    return (
        papers_list,
        title,
        json.dumps(expanded_rows),
        pathname,
        sort_desc_active,
        sort_asc_active,
        sort_order,
        total_pages,
        pagination_info,
    )


def extract_github_links(paper):
    github_links = json.loads(paper.get("github_links", "[]"))
    return github_links if github_links else []


def create_paper_item(paper, is_expanded):
    github_links = extract_github_links(paper)
    has_github = bool(github_links)

    github_icon = html.Div(
        [
            (
                html.A(
                    html.I(className="fab fa-github github-icon"),
                    href=github_links[0] if has_github else None,
                    target="_blank",
                    id={"type": "github-icon", "index": paper["paper_id"]},
                    style={
                        "color": "inherit",
                        "cursor": "pointer",
                        "font-size": "20px",
                        "justify-content": "center",
                        "align-items": "center",
                        "height": "100%",
                    },
                    **{"data-stop-propagation": True},
                )
                if has_github
                else None
            ),
            dbc.Tooltip(
                ("Click to open GitHub repository" if has_github else "No GitHub repository"),
                target={"type": "github-icon", "index": paper["paper_id"]},
                placement="top",
            ),
        ],
        style={"height": "100%"},
    )

    citation_count = html.Div(
        [
            html.Span(
                id={"type": "citation-display", "index": paper["paper_id"]},
                children=str(paper.get("citations", "N/A")),
            ),
            dbc.Tooltip(
                "Number of citations",
                target={"type": "citation-display", "index": paper["paper_id"]},
                placement="top",
            ),
        ],
        id={"type": "paper-citations", "index": paper["paper_id"]},
    )

    return html.Div(
        [
            dbc.ListGroupItem(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                html.Div(
                                    [
                                        html.A(
                                            paper["paper_id"],
                                            href=f"https://arxiv.org/abs/{paper['paper_id']}",
                                            target="_blank",
                                            className="paper-id",
                                        ),
                                        dbc.Tooltip(
                                            "Click to open arXiv page",
                                            target={
                                                "type": "paper-id",
                                                "index": paper["paper_id"],
                                            },
                                            placement="top",
                                        ),
                                    ],
                                    id={"type": "paper-id", "index": paper["paper_id"]},
                                ),
                                width=1,
                            ),
                            dbc.Col(
                                [
                                    html.Div(
                                        [
                                            html.Strong(paper["title"], className="paper-title"),
                                            html.Div(
                                                paper["relevance_score_brief_explanation"],
                                                className="paper-explanation mt-2",
                                            ),
                                            dbc.Tooltip(
                                                "Click to expand/collapse",
                                                target={
                                                    "type": "paper-title",
                                                    "index": paper["paper_id"],
                                                },
                                                placement="top",
                                            ),
                                        ],
                                        id={
                                            "type": "paper-title",
                                            "index": paper["paper_id"],
                                        },
                                    )
                                ],
                                width=8,
                            ),
                            dbc.Col(
                                html.Div(
                                    [
                                        html.Span(
                                            paper["published"][:10],
                                            className="paper-date",
                                        ),
                                        dbc.Tooltip(
                                            "Publication date",
                                            target={
                                                "type": "paper-date",
                                                "index": paper["paper_id"],
                                            },
                                            placement="top",
                                        ),
                                    ],
                                    id={"type": "paper-date", "index": paper["paper_id"]},
                                ),
                                width=1,
                            ),
                            dbc.Col(
                                [
                                    html.Div(
                                        [
                                            html.Span(
                                                f"{paper['relevance_score']:.2f}",
                                                className="paper-relevance",
                                            ),
                                            dbc.Tooltip(
                                                "Relevance score",
                                                target={
                                                    "type": "paper-relevance",
                                                    "index": paper["paper_id"],
                                                },
                                                placement="top",
                                            ),
                                        ],
                                        id={
                                            "type": "paper-relevance",
                                            "index": paper["paper_id"],
                                        },
                                        className="mb-2",
                                    ),
                                    html.Div(citation_count, className="mb-2"),
                                    html.Div(github_icon, className="mb-2"),
                                ],
                                width=1,
                            ),
                            dbc.Col(
                                html.Div(
                                    [
                                        html.I(
                                            className=f"fas fa-chevron-down fa-lg expand-icon {'rotate' if is_expanded else ''}"
                                        ),
                                        dbc.Tooltip(
                                            "Click to expand/collapse",
                                            target={
                                                "type": "expand-icon",
                                                "index": paper["paper_id"],
                                            },
                                            placement="top",
                                        ),
                                    ],
                                    id={
                                        "type": "expand-icon",
                                        "index": paper["paper_id"],
                                    },
                                ),
                                width=1,
                            ),
                        ],
                        align="center",
                        className="paper-row",
                    ),
                ],
                id={"type": "paper-row", "index": paper["paper_id"]},
                className=f"clickable-row {'expanded' if is_expanded else ''}",
            ),
            dbc.Collapse(
                dbc.Card(dbc.CardBody(create_paper_details(paper)), className="paper-details"),
                id={"type": "paper-collapse", "index": paper["paper_id"]},
                is_open=is_expanded,
            ),
        ]
    )


def create_paper_details(paper):
    github_links = extract_github_links(paper)

    details = [
        html.Div([html.Span(dcc.Markdown(paper["relevance_score_explanation"]))]),
        html.Div([html.Strong("Abstract: "), html.Span(paper["abstract"])]),
        html.Div([html.Strong("Authors: "), html.Span(paper["authors"])]),
        html.Div([html.Strong("Published: "), html.Span(paper["published"])]),
        html.Div([html.Strong("Categories: "), html.Span(paper["categories"])]),
        html.Div(
            [
                html.Strong("Citations: "),
                html.Span(
                    id={"type": "citation-display-detail", "index": paper["paper_id"]},
                    children=str(paper.get("citations", "N/A")),
                ),
            ]
        ),
    ]

    if github_links:
        github_section = html.Div(
            [
                html.Strong("GitHub: "),
                html.Span([html.A(link, href=link, target="_blank", className="paper-id mr-2") for link in github_links]),
            ]
        )
        details.append(github_section)

    return html.Div(details)


@callback(
    Output({"type": "paper-collapse", "index": MATCH}, "is_open"),
    Output({"type": "paper-row", "index": MATCH}, "className"),
    Output({"type": "expand-icon", "index": MATCH}, "children"),
    Input({"type": "paper-row", "index": MATCH}, "n_clicks"),
    State({"type": "paper-collapse", "index": MATCH}, "is_open"),
    State({"type": "expand-icon", "index": MATCH}, "children"),
    State({"type": "paper-row", "index": MATCH}, "id"),
    prevent_initial_call=True,
)
def toggle_paper_collapse(n_clicks, is_open, icon, row_id):
    ctx = dash.callback_context
    if not ctx.triggered:
        return is_open, "clickable-row", icon

    prop_id = ctx.triggered[0]["prop_id"]
    if "github-icon" in prop_id or "sort-desc" in prop_id or "sort-asc" in prop_id:
        raise PreventUpdate

    if n_clicks:
        new_is_open = not is_open
        className = "clickable-row expanded" if new_is_open else "clickable-row"

        # Update the icon's class to include or remove 'rotate'
        icon[0]["props"]["className"] = f"fas fa-chevron-down fa-lg expand-icon {'rotate' if new_is_open else ''}"

        return new_is_open, className, icon
    return is_open, "clickable-row", icon


@callback(Output("query-text", "children"), Input("url", "search"))
def update_query_text(search):
    if not search:
        raise PreventUpdate
    query_id = search.split("=")[-1]
    query = DbOperations.get_query(query_id)
    return query["query_text"] if query else ""


@callback(
    Output("text-filter", "value"),
    Input("clear-text-filter", "n_clicks"),
    State("text-filter", "value"),
    prevent_initial_call=True,
)
def clear_text_filter(n_clicks, current_value):
    if n_clicks and current_value:
        return ""
    raise PreventUpdate


@callback(Output("clear-text-filter", "style"), Input("text-filter", "value"))
def toggle_clear_button(value):
    if value:
        return {"display": "flex"}
    return {"display": "none"}


@callback(
    Output("github-filter", "className"),
    Output("github-filter", "color"),
    Input("github-filter", "n_clicks"),
    State("github-filter", "className"),
    prevent_initial_call=True,
)
def toggle_github_filter(n_clicks, current_class):
    if n_clicks:
        if "active" in current_class:
            return "github-filter-btn", "light"
        else:
            return "github-filter-btn active", "primary"
    raise PreventUpdate


@callback(
    Output("pagination", "active_page"),
    Input("pagination", "active_page"),
    Input("order-by", "value"),
    Input("relevance-filter", "value"),
    Input("text-filter", "value"),
    Input("github-filter", "className"),
    Input("papers-per-page", "value"),
)
def update_active_page(
    active_page,
    order_by,
    relevance_filter,
    text_filter,
    github_filter_class,
    papers_per_page,
):
    ctx = dash.callback_context
    triggered_input = ctx.triggered[0]["prop_id"] if ctx.triggered else None

    if triggered_input and triggered_input not in [
        "pagination.active_page",
        "papers-per-page.value",
    ]:
        return 1  # Reset to first page when filters change
    return active_page or 1  # Default to first page if None
