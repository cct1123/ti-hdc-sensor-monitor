"""Monitor display helpers, including the local-time history viewport."""

from datetime import datetime, timedelta
from typing import Iterable

import plotly.graph_objects as go
from dash import html
from plotly.subplots import make_subplots

from ..models import Sample

PLOT_WINDOW = timedelta(minutes=5)


def _local_time(value: datetime) -> datetime:
    # Plotly date strings should contain the computer's wall-clock time, without
    # a timezone suffix that a browser might reinterpret. CSV stays in UTC.
    return value.astimezone().replace(tzinfo=None)


def _plot_time(value) -> datetime:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000)
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return _local_time(parsed) if parsed.tzinfo is not None else parsed


def _plot_range(current, relayout, reset=False):
    """None follows live data; an explicit range stays fixed across refreshes."""
    relayout = dict(relayout or {})
    for key, value in list(relayout.items()):
        if key.startswith("xaxis2."):
            relayout[key.replace("xaxis2.", "xaxis.")] = value
    if reset or relayout.get("xaxis.autorange"):
        return None
    selected = relayout.get("xaxis.range")
    if selected is None and "xaxis.range[0]" in relayout and "xaxis.range[1]" in relayout:
        selected = [relayout["xaxis.range[0]"], relayout["xaxis.range[1]"]]
    if selected is not None:
        try:
            start, end = (_plot_time(value) for value in selected)
            if start < end:
                return [start.isoformat(), end.isoformat()]
        except (TypeError, ValueError, OverflowError):
            pass
    return current


def _metric_card(label: str, value_id: str, value: str = "--") -> html.Div:
    return html.Div(
        [
            html.Div(className="metric-marker"),
            html.Div(
                [
                    html.Div(label, className="metric-label"),
                    html.Div(value, id=value_id, className="metric-value"),
                ]
            ),
        ],
        className="metric-card",
    )


def _channel_figure(
    samples: Iterable[Sample], view_range=None, field="temperature_c", unit="°C", color="#7167f4"
) -> go.Figure:
    points = list(samples)
    local_times = [_local_time(sample.timestamp_utc) for sample in points]
    if view_range:
        start, end = (_plot_time(value) for value in view_range)
    else:
        end = (local_times[-1] if points else datetime.now()) + timedelta(seconds=1)
        start = end - PLOT_WINDOW
    figure = go.Figure()
    if points:
        figure.add_trace(
            go.Scatter(
                x=local_times,
                y=[getattr(sample, field) for sample in points],
                mode="lines+markers",
                marker={"size": 3},
                line={"color": color, "width": 2.5},
                hovertemplate="%{x|%Y-%m-%d %H:%M:%S}<br>%{y:.3f} " + unit + "<extra></extra>",
                name="Temperature" if field == "temperature_c" else "Relative humidity",
            )
        )
    figure.update_xaxes(
        type="date",
        range=[start, end],
        autorange=False,
        showgrid=True,
        gridcolor="#eceef4",
        zeroline=False,
        tickformat="%H:%M:%S\n%b %d",
        fixedrange=False,
    )
    visible_values = [
        getattr(point, field) for point, timestamp in zip(points, local_times) if start <= timestamp <= end
    ]
    # Include the line where it crosses either window edge. A zoomed window
    # can contain a visible segment even when both of its samples are outside.
    for left, right, left_time, right_time in zip(points, points[1:], local_times, local_times[1:]):
        for edge in (start, end):
            if left_time < edge < right_time:
                fraction = (edge - left_time) / (right_time - left_time)
                visible_values.append(
                    getattr(left, field) + fraction * (getattr(right, field) - getattr(left, field))
                )
    # Keep all buffered points in the trace so panning can reveal history, but
    # scale temperature to the selected window instead of off-screen outliers.
    values = visible_values or [getattr(point, field) for point in points]
    if values:
        low, high = min(values), max(values)
        padding = max(0.02, (high - low) * 0.1)
        figure.update_yaxes(range=[low - padding, high + padding], autorange=False)
    figure.update_yaxes(
        showgrid=True,
        gridcolor="#eceef4",
        zeroline=False,
        rangemode="normal",
        fixedrange=True,
        visible=bool(points),
    )
    return figure


def history_figure(samples, view_range=None):
    points = list(samples)
    temperature = _channel_figure(points, view_range)
    humidity = _channel_figure(points, view_range, "relative_humidity_pct", "%RH", "#26a98f")
    figure = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.09)
    for row, channel, title in ((1, temperature, "Temperature (°C)"), (2, humidity, "Humidity (%RH)")):
        for trace in channel.data:
            trace.marker.color = ["#ef9c69" if sample.heater_on else trace.line.color for sample in points]
            trace.customdata = ["Heater on" if sample.heater_on else "Heater off" for sample in points]
            trace.hovertemplate = trace.hovertemplate.replace("<extra>", "<br>%{customdata}<extra>")
            figure.add_trace(trace, row=row, col=1)
        figure.update_xaxes(channel.layout.xaxis.to_plotly_json(), row=row, col=1)
        figure.update_yaxes(channel.layout.yaxis.to_plotly_json(), title_text=title, row=row, col=1)
    figure.update_layout(
        margin=dict(l=65, r=24, t=20, b=40),
        height=500,
        showlegend=False,
        paper_bgcolor="white",
        plot_bgcolor="#fbfbfd",
        hovermode="x unified",
        uirevision="history" if view_range else "live",
        dragmode="pan",
        font=dict(color="#596176", family="Inter, system-ui, sans-serif"),
    )
    figure.update_xaxes(matches="x2", title_text=None, row=1, col=1)
    figure.update_xaxes(title_text="Computer time (local)", row=2, col=1)
    if not points:
        figure.add_annotation(
            text="Press Start monitoring to begin sampling",
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
            font=dict(color="#768198"),
        )
    return figure
