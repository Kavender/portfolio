import numpy as np
import plotly.express as px
import plotly.graph_objects as go


def draw_correlation_heatmap(df_corr, title):
    mask = np.triu(np.ones_like(df_corr, dtype=bool))
    corr_heatmap = go.Heatmap(
        z=df_corr.mask(mask),
        x=df_corr.columns,
        y=df_corr.columns,
        colorscale=px.colors.diverging.RdBu,
        zmin=-1,
        zmax=1
    )
    layout = go.Layout(
        title_text=title, 
        title_x=0.5, 
        width=600, 
        height=600,
        xaxis_showgrid=False,
        yaxis_showgrid=False,
        yaxis_autorange='reversed',
        dragmode = "zoom",
    )

    fig=go.Figure(data=[corr_heatmap], layout=layout)
    return fig