with st.expander("💰 Remuneration Details", expanded=True):
    remuneration = result.get("remuneration_details", {})

    # ----- LEFT SIDE -----
    col1, col2 = st.columns([2, 1])
    with col1:
        st.write("**Marked Options:**")
        for option in remuneration.get("marked_options", []):
            st.write(f"- {option.get('option', 'N/A')}")
            amount = option.get("amount", "")
            currency = option.get("currency", "")
            upper_limit = option.get("upper_limit", "")

            if amount not in ["Missing", "N/A", None, ""]:
                st.write(f"  • Amount: {amount} {currency}")

            if upper_limit not in ["Missing", "N/A", None, ""]:
                st.write(f"  • Upper Limit: {upper_limit} {currency}")

            if option.get("rate_card_status") not in ["N/A", None]:
                st.write(f"  • Rate Card: {option.get('rate_card_status')}")

            if option.get("table_status") not in ["N/A", None]:
                st.write(f"  • Table: {option.get('table_status')}")

    # ----- RIGHT SIDE -----
    with col2:
        status = remuneration.get("validation_status", "N/A")
        st.markdown(f"**Status:** <span class='{get_status_style(status)}'>{status}</span>",
                    unsafe_allow_html=True)

    st.info(remuneration.get("validation_reason", "No details provided"))

    # ----- SHOW THE TABLE -----
    rate_table = remuneration.get("rate_table")

    if rate_table and "headers" in rate_table and "rows" in rate_table:
        st.subheader("📄 Extracted Rate Table")

        df_table = pd.DataFrame(rate_table["rows"], columns=rate_table["headers"])
        st.table(df_table)
    else:
        st.warning("No rate table extracted.")
