import streamlit as st
import pandas as pd
from components.charts import radar_chart, score_badge
from components.pdf_export import generate_panel_pdf
from components.state import init_session_state

init_session_state()

st.title("Panel Review")
st.caption("Review all panels created during this session — view composition details, AI health scores, and export panel data as CSV or PDF.")

panels = st.session_state.created_panels

if not panels:
    st.info("No panels created yet. Go to **Create Panel** to build your first panel.")
    st.stop()

st.metric("Total Panels Created", len(panels))

for i, panel in enumerate(panels):
    with st.expander(
        f"Panel {i + 1}: {panel.get('post_name', 'Untitled')} — "
        f"{panel.get('panel_type', '')} | "
        f"Score: {panel.get('health', {}).get('overall', 'N/A')}",
        expanded=(i == len(panels) - 1),
    ):
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("File No", panel.get("file_no", "N/A"))
        col2.metric("Panel Type", panel.get("panel_type", "N/A"))
        col3.metric("Advisors", len(panel.get("selected_advisors", [])))
        col4.metric("Boards", panel.get("num_boards", 1))

        # Board details
        st.caption("Board configuration with assigned presidents, advisor counts, and interview dates.")
        boards = panel.get("boards", [])
        if boards:
            st.markdown("**Boards:**")
            board_df = pd.DataFrame(boards)
            st.dataframe(board_df, use_container_width=True, hide_index=True)

        # Selected advisors
        advisors = panel.get("selected_advisors", [])
        if advisors:
            st.markdown("**Selected Advisors:**")
            adv_df = pd.DataFrame(advisors)
            display_cols = ["INDEX_NO", "PROFESSION_NAME", "DESIGNATION_DESC",
                            "ZONE_NAME", "GENDER", "EMPLOYMENT_STATUS", "composite_score"]
            available = [c for c in display_cols if c in adv_df.columns]
            st.dataframe(adv_df[available], use_container_width=True, hide_index=True)

        # Health card
        st.caption("AI-generated health card showing panel diversity and balance across gender, zone, experience, and expertise dimensions.")
        health = panel.get("health", {})
        if health:
            col1, col2 = st.columns([1, 1])
            with col1:
                dim_labels = {
                    "gender": "Gender Balance",
                    "zone": "Zone Diversity",
                    "experience": "Experience Mix",
                    "expertise": "Expertise Coverage",
                }
                fig = radar_chart(
                    dim_labels,
                    {dim_labels[k]: v for k, v in health.get("scores", {}).items()},
                    title=f"Panel {i + 1} Health",
                )
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                st.markdown("### Overall Score")
                st.markdown(
                    score_badge(health.get("overall", 0)),
                    unsafe_allow_html=True,
                )

                if health.get("suggestions"):
                    st.markdown("**Suggestions:**")
                    for s in health["suggestions"]:
                        st.caption(f"- {s}")

                if health.get("conflicts"):
                    st.markdown("**Conflicts:**")
                    for c in health["conflicts"]:
                        st.caption(f"- {c}")

        # Export
        if advisors:
            col_csv, col_pdf = st.columns(2)
            with col_csv:
                adv_df_full = pd.DataFrame(advisors)
                csv = adv_df_full.to_csv(index=False)
                st.download_button(
                    f"Download Panel {i + 1} as CSV",
                    csv,
                    f"panel_{i + 1}.csv",
                    "text/csv",
                )
            with col_pdf:
                pdf_bytes = generate_panel_pdf(panel, i + 1)
                st.download_button(
                    f"Download Panel {i + 1} as PDF",
                    pdf_bytes,
                    f"panel_{i + 1}.pdf",
                    "application/pdf",
                )
