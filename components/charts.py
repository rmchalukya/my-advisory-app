import plotly.graph_objects as go
import plotly.express as px
import streamlit as st


def radar_chart(dimensions, scores, title="Panel Health Card"):
    """Render a radar chart for panel health dimensions."""
    categories = list(dimensions)
    values = [scores.get(d, 0) for d in categories]
    # Close the polygon
    categories.append(categories[0])
    values.append(values[0])

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill="toself",
        name="Panel Score",
        line_color="#1f77b4",
        fillcolor="rgba(31, 119, 180, 0.25)",
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100]),
        ),
        showlegend=False,
        title=title,
        height=400,
    )
    return fig


def score_badge(score):
    """Return a colored HTML badge for a score."""
    if score >= 70:
        color = "#28a745"
        label = "Good"
    elif score >= 40:
        color = "#ffc107"
        label = "Fair"
    else:
        color = "#dc3545"
        label = "Needs Improvement"

    return (
        f'<div style="display:inline-block; padding:4px 12px; border-radius:12px; '
        f'background:{color}; color:white; font-weight:bold; font-size:14px;">'
        f'{score:.0f} - {label}</div>'
    )


def horizontal_bar(data, x_col, y_col, title="", color=None, height=400):
    fig = px.bar(
        data, x=x_col, y=y_col, orientation="h",
        title=title, color=color, height=height,
    )
    fig.update_layout(yaxis=dict(autorange="reversed"), showlegend=False)
    return fig


def pie_chart(data, names_col, values_col, title="", height=350):
    fig = px.pie(data, names=names_col, values=values_col, title=title, height=height)
    fig.update_traces(textposition="inside", textinfo="percent+label")
    return fig


def heatmap(pivot_df, title="", height=500):
    fig = px.imshow(
        pivot_df,
        labels=dict(x="Column", y="Row", color="Count"),
        title=title,
        height=height,
        aspect="auto",
        color_continuous_scale="Blues",
    )
    return fig


def time_series(data, x_col, y_col, title="", height=400):
    fig = px.line(data, x=x_col, y=y_col, title=title, height=height, markers=True)
    return fig


def grouped_bar(data, x_col, y_cols, labels, title="", height=400):
    """Side-by-side grouped bar chart for comparing two metrics."""
    fig = go.Figure()
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]
    for i, (col, label) in enumerate(zip(y_cols, labels)):
        fig.add_trace(go.Bar(
            x=data[x_col], y=data[col], name=label,
            marker_color=colors[i % len(colors)],
        ))
    fig.update_layout(
        barmode="group", title=title, height=height,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig


def funnel_chart(stages, values, title="", height=350):
    """Horizontal funnel chart showing progressive drop-off."""
    fig = go.Figure(go.Funnel(
        y=stages, x=values,
        textinfo="value+percent initial",
        marker=dict(color=["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"][:len(stages)]),
    ))
    fig.update_layout(title=title, height=height)
    return fig


def stacked_bar(data, x_col, y_cols, labels, title="", height=400):
    """Stacked bar chart for composition breakdown."""
    fig = go.Figure()
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]
    for i, (col, label) in enumerate(zip(y_cols, labels)):
        fig.add_trace(go.Bar(
            x=data[x_col], y=data[col], name=label,
            marker_color=colors[i % len(colors)],
        ))
    fig.update_layout(
        barmode="stack", title=title, height=height,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig
