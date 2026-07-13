from datetime import datetime, date
import io

import pandas as pd
import streamlit as st

import db
import suggestions as sug
import forecast as fc

st.set_page_config(page_title="Space Cleaning — Pricing & Revenue", page_icon="🧼", layout="wide")
db.init_db()

PAGES = [
    "📊 Dashboard",
    "💡 Pricing & Competitors",
    "📈 Revenue Forecast",
    "🔧 Job Calculator",
    "💼 Job Tracker",
    "📤 Export",
]

st.sidebar.title("🧼 Space Cleaning")
st.sidebar.caption("Pricing & Revenue Manager")
page = st.sidebar.radio("Navigate", PAGES)
st.sidebar.markdown("---")
st.sidebar.caption("Shared data — visible to your whole team.")


def money(x):
    return f"${x:,.2f}" if x is not None else "—"


# =============================================================================
# DASHBOARD
# =============================================================================
if page == "📊 Dashboard":
    st.title("📊 Dashboard")

    services = db.get_services()
    comp_prices = db.get_competitor_prices()
    jobs = db.get_jobs()

    if not services:
        st.info("No services yet. Add some on the **Pricing & Competitors** page.")
        st.stop()

    # ---- KPI row ----
    jobs_df = pd.DataFrame(jobs) if jobs else pd.DataFrame(columns=["price_charged", "total_cost", "status", "job_date"])
    completed = jobs_df[jobs_df["status"].isin(["Completed", "Paid"])] if not jobs_df.empty else jobs_df
    total_revenue = completed["price_charged"].sum() if not completed.empty else 0
    total_cost = completed["total_cost"].sum() if not completed.empty and "total_cost" in completed else 0
    total_margin = total_revenue - total_cost
    margin_pct = (total_margin / total_revenue * 100) if total_revenue else 0
    job_count = len(completed)

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Revenue", money(total_revenue))
    k2.metric("Total Margin", money(total_margin), f"{margin_pct:.1f}%")
    k3.metric("Jobs Completed", job_count)
    k4.metric("Services Tracked", len(services))
    k5.metric("Competitors Tracked", len(db.get_competitors()))

    st.markdown("---")

    col1, col2 = st.columns(2)

    # ---- Your prices vs market bar chart ----
    with col1:
        st.subheader("Your Prices vs Market")
        rows = []
        for s in services:
            stats = sug.compute_competitor_stats(s["id"], comp_prices)
            rows.append({
                "Service": s["name"],
                "Our Rate": s["our_rate"],
                "Market Avg": stats["avg"] if stats else None,
            })
        chart_df = pd.DataFrame(rows).dropna(subset=["Our Rate"], how="all")
        if not chart_df.empty:
            chart_df = chart_df.set_index("Service")
            st.bar_chart(chart_df)
        else:
            st.caption("Add your rates to see this comparison.")

    # ---- Revenue by service pie ----
    with col2:
        st.subheader("Revenue by Service")
        if not completed.empty:
            by_service = completed.groupby("service_name")["price_charged"].sum()
            if not by_service.empty:
                import plotly.express as px
                pie_df = by_service.reset_index()
                pie_df.columns = ["Service", "Revenue"]
                fig = px.pie(pie_df, names="Service", values="Revenue", hole=0.3)
                fig.update_traces(textinfo="percent+label")
                st.plotly_chart(fig, width="stretch")
            else:
                st.caption("No completed jobs yet.")
        else:
            st.caption("Log jobs in the Job Tracker to see revenue breakdown.")

    st.markdown("---")

    # ---- Monthly trend ----
    st.subheader("Monthly Revenue Trend")
    hist = fc.monthly_revenue_history(jobs)
    if not hist.empty:
        st.line_chart(hist.set_index("month"))
    else:
        st.caption("No completed/paid jobs yet — log some in the Job Tracker to see the trend.")


# =============================================================================
# PRICING & COMPETITORS (unified page)
# =============================================================================
elif page == "💡 Pricing & Competitors":
    st.title("💡 Pricing & Competitors")
    st.caption("Manage your services, set rates, log competitor prices, and get a strategy-based suggestion — all in one place.")

    services = db.get_services()
    competitors = db.get_competitors()
    comp_prices = db.get_competitor_prices()

    # ---- Strategy selector (applies to whole page) ----
    st.markdown("### Strategy")
    strat_col1, strat_col2 = st.columns([2, 1])
    with strat_col1:
        strategy_key = st.radio(
            "Positioning strategy",
            list(sug.STRATEGIES.keys()),
            format_func=lambda k: sug.STRATEGIES[k]["label"],
            horizontal=True,
            index=list(sug.STRATEGIES.keys()).index(db.get_setting("strategy", "market")),
        )
        db.set_setting("strategy", strategy_key)
    with strat_col2:
        custom_pct = st.number_input(
            "Override % vs market avg (optional)",
            value=float(sug.STRATEGIES[strategy_key]["pct"]),
            step=1.0,
        )

    st.markdown("---")

    # ---- Add new service ----
    with st.expander("➕ Add a new service"):
        with st.form("add_service", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns(4)
            name = c1.text_input("Service name")
            category = c2.text_input("Category", value="Residential")
            unit = c3.selectbox("Pricing unit", db.PRICING_UNITS)
            rate = c4.number_input("Our rate ($)", min_value=0.0, step=5.0)
            if st.form_submit_button("Add Service"):
                if name.strip():
                    db.add_service(name.strip(), category.strip(), unit, rate)
                    st.success(f"Added '{name}'")
                    st.rerun()
                else:
                    st.error("Service name required.")

    # ---- Add new competitor (kept on this page, not separate) ----
    with st.expander("➕ Add a competitor"):
        with st.form("add_competitor", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            cname = c1.text_input("Competitor name")
            website = c2.text_input("Website")
            area = c3.text_input("Service area")
            if st.form_submit_button("Add Competitor"):
                if cname.strip():
                    db.add_competitor(cname.strip(), website.strip(), area.strip())
                    st.success(f"Added '{cname}'")
                    st.rerun()
                else:
                    st.error("Competitor name required.")

    if not services:
        st.info("Add a service above to get started.")
        st.stop()

    st.markdown("---")
    st.markdown("### Services — rates, market comparison, and suggestions")

    service_names = {s["id"]: s["name"] for s in services}
    competitor_names = {c["id"]: c["name"] for c in competitors}

    for s in services:
        stats = sug.compute_competitor_stats(s["id"], comp_prices)
        target = sug.suggested_price(stats, strategy_key, custom_pct)
        status, emoji, message = sug.evaluate_service(s["our_rate"], stats, target)

        header = f"{emoji} **{s['name']}** ({s['category'] or '—'}) — {s['pricing_unit']}"
        with st.expander(header, expanded=False):
            top1, top2, top3, top4 = st.columns(4)
            top1.metric("Our Rate", money(s["our_rate"]))
            top2.metric("Market Avg", money(stats["avg"]) if stats else "—")
            top3.metric("Suggested", money(target) if target else "—")
            top4.metric("Competitors Logged", stats["count"] if stats else 0)
            st.caption(message)

            # inline price update
            ic1, ic2 = st.columns([1, 3])
            with ic1:
                new_rate = st.number_input(
                    "Update our rate", min_value=0.0, value=float(s["our_rate"] or 0),
                    step=5.0, key=f"rate_{s['id']}"
                )
                if st.button("💾 Save rate", key=f"save_rate_{s['id']}"):
                    db.update_service_rate(s["id"], new_rate)
                    st.success("Updated.")
                    st.rerun()

            with ic2:
                if stats:
                    comp_rows = [
                        {"Competitor": cp["competitor_name"], "Rate": cp["rate"], "Unit": cp["pricing_unit"]}
                        for cp in comp_prices if cp["service_id"] == s["id"]
                    ]
                    chart_df = pd.DataFrame(comp_rows)
                    chart_df.loc[len(chart_df)] = {"Competitor": "US (Space Cleaning)", "Rate": s["our_rate"], "Unit": s["pricing_unit"]}
                    st.bar_chart(chart_df.set_index("Competitor")["Rate"])
                else:
                    st.caption("No competitor prices logged for this service yet — add one below.")

            st.markdown("###### Log / update a competitor price for this service")
            if competitors:
                with st.form(f"log_price_{s['id']}", clear_on_submit=True):
                    lc1, lc2, lc3, lc4 = st.columns(4)
                    comp_choice = lc1.selectbox("Competitor", list(competitor_names.values()), key=f"compsel_{s['id']}")
                    comp_rate = lc2.number_input("Rate ($)", min_value=0.0, step=5.0, key=f"comprate_{s['id']}")
                    comp_unit = lc3.selectbox("Unit", db.PRICING_UNITS,
                                               index=db.PRICING_UNITS.index(s["pricing_unit"]) if s["pricing_unit"] in db.PRICING_UNITS else 0,
                                               key=f"compunit_{s['id']}")
                    source = lc4.text_input("Source note", key=f"compsource_{s['id']}")
                    if st.form_submit_button("Save competitor price"):
                        comp_id = [cid for cid, cname in competitor_names.items() if cname == comp_choice][0]
                        db.upsert_competitor_price(comp_id, s["id"], comp_rate, comp_unit, source)
                        st.success("Saved.")
                        st.rerun()
            else:
                st.caption("Add a competitor above first.")

            del_col1, del_col2 = st.columns(2)
            if del_col1.button("🗑️ Delete this service", key=f"delserv_{s['id']}"):
                db.delete_service(s["id"])
                st.warning(f"Deleted '{s['name']}'.")
                st.rerun()

    if competitors:
        st.markdown("---")
        st.markdown("### Competitors")
        for c in competitors:
            cc1, cc2, cc3, cc4 = st.columns([2, 2, 2, 1])
            cc1.write(f"**{c['name']}**")
            cc2.write(c["website"] or "—")
            cc3.write(c["service_area"] or "—")
            if cc4.button("🗑️", key=f"delcomp_{c['id']}"):
                db.delete_competitor(c["id"])
                st.rerun()


# =============================================================================
# REVENUE FORECAST
# =============================================================================
elif page == "📈 Revenue Forecast":
    st.title("📈 Revenue Forecast")

    jobs = db.get_jobs()
    hist = fc.monthly_revenue_history(jobs)

    if hist.empty:
        st.info("No completed/paid job history yet. Log jobs in the Job Tracker, or manually set a baseline below.")
        base_default = 0.0
    else:
        base_default = float(hist["revenue"].iloc[-1])
        st.subheader("Actual monthly revenue so far")
        st.line_chart(hist.set_index("month"))

    st.markdown("---")
    st.subheader("Projection settings")

    c1, c2, c3 = st.columns(3)
    base_revenue = c1.number_input("Starting monthly revenue ($)", min_value=0.0, value=base_default, step=100.0)
    growth_pct = c2.number_input("Expected monthly growth (%)", value=5.0, step=0.5)
    num_months = c3.slider("Months to project", min_value=3, max_value=24, value=12)

    target = st.number_input("Optional target monthly revenue ($) — shown as a line on the chart", min_value=0.0, value=0.0, step=100.0)
    target = target if target > 0 else None

    proj = fc.project_forecast(base_revenue, growth_pct, num_months, target)

    st.markdown("---")
    st.subheader("Projected revenue")

    chart_data = proj.set_index("Month")[["Projected Revenue"]].copy()
    if target:
        chart_data["Target"] = target
    st.line_chart(chart_data)

    st.dataframe(proj, width="stretch", hide_index=True,
                 column_config={
                     "Projected Revenue": st.column_config.NumberColumn(format="$%.2f"),
                     "Target": st.column_config.NumberColumn(format="$%.2f"),
                 })

    end_revenue = proj["Projected Revenue"].iloc[-1]
    total_projected = proj["Projected Revenue"].sum()
    m1, m2 = st.columns(2)
    m1.metric(f"Revenue in month {num_months}", money(end_revenue), f"{growth_pct}%/mo compounding")
    m2.metric(f"Total projected over {num_months} months", money(total_projected))


# =============================================================================
# JOB CALCULATOR
# =============================================================================
elif page == "🔧 Job Calculator":
    st.title("🔧 Job Calculator")
    st.caption("Work out margin and break-even price for a single job, and see how your quote stacks up against the market.")

    services = db.get_services()
    comp_prices = db.get_competitor_prices()

    if not services:
        st.info("Add a service first on the Pricing & Competitors page.")
        st.stop()

    service_names = {s["id"]: s["name"] for s in services}

    c1, c2 = st.columns(2)
    with c1:
        service_choice = st.selectbox("Service", list(service_names.values()))
        service_id = [sid for sid, sname in service_names.items() if sname == service_choice][0]
        service = db.get_service(service_id)

        quoted_price = st.number_input("Price you plan to charge ($)", min_value=0.0,
                                        value=float(service["our_rate"] or 0), step=5.0)
        total_cost = st.number_input("Total cost for this job ($) — labor, supplies, travel, everything", min_value=0.0, step=5.0)

    with c2:
        margin = quoted_price - total_cost
        margin_pct = (margin / quoted_price * 100) if quoted_price else 0
        break_even = total_cost  # price at which margin = 0

        st.metric("Margin", money(margin), f"{margin_pct:.1f}%")
        st.metric("Break-even price", money(break_even))

        # Margin gauge (simple progress bar as gauge substitute)
        gauge_pct = max(0, min(margin_pct, 100)) / 100
        st.progress(gauge_pct, text=f"Margin health: {margin_pct:.1f}%")
        if margin_pct < 15:
            st.warning("Thin margin — consider raising the price or cutting cost.")
        elif margin_pct > 50:
            st.success("Healthy margin.")
        else:
            st.info("Reasonable margin.")

    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Cost vs Margin breakdown")
        if quoted_price > 0:
            values = [max(total_cost, 0), max(margin, 0)]
            labels = ["Cost", "Margin"]
            if sum(values) > 0:
                import plotly.express as px
                pie_df = pd.DataFrame({"Label": labels, "Amount": values})
                fig = px.pie(pie_df, names="Label", values="Amount", hole=0.3,
                             color="Label", color_discrete_map={"Cost": "#e07a5f", "Margin": "#81b29a"})
                fig.update_traces(textinfo="percent+label")
                st.plotly_chart(fig, width="stretch")
        else:
            st.caption("Enter a quoted price to see the breakdown.")

    with col2:
        st.subheader("Market comparison")
        stats = sug.compute_competitor_stats(service_id, comp_prices)
        if stats:
            comp_df = pd.DataFrame([
                {"Label": "Your Quote", "Rate": quoted_price},
                {"Label": "Market Min", "Rate": stats["min"]},
                {"Label": "Market Avg", "Rate": stats["avg"]},
                {"Label": "Market Max", "Rate": stats["max"]},
            ])
            st.bar_chart(comp_df.set_index("Label"))
        else:
            st.caption("No competitor data logged for this service yet.")


# =============================================================================
# JOB TRACKER
# =============================================================================
elif page == "💼 Job Tracker":
    st.title("💼 Job Tracker")

    services = db.get_services()
    employees = db.get_employees()

    with st.expander("➕ Log a new job", expanded=not db.get_jobs()):
        if not services:
            st.warning("Add a service first on the Pricing & Competitors page.")
        else:
            with st.form("add_job", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                client = c1.text_input("Client name")
                service_choice = c2.selectbox("Service", [s["name"] for s in services])
                job_date = c3.date_input("Job date", value=date.today())

                c4, c5, c6 = st.columns(3)
                price_charged = c4.number_input("Price charged ($)", min_value=0.0, step=5.0)
                total_cost = c5.number_input("Total cost ($)", min_value=0.0, step=5.0)
                status = c6.selectbox("Status", db.JOB_STATUSES)

                c7, c8 = st.columns(2)
                emp_options = ["— unassigned —"] + [e["name"] for e in employees]
                emp_choice = c7.selectbox("Employee / crew", emp_options)
                notes = c8.text_input("Notes")

                if st.form_submit_button("Add Job"):
                    service_id = [s["id"] for s in services if s["name"] == service_choice][0]
                    employee_id = None
                    if emp_choice != "— unassigned —":
                        employee_id = [e["id"] for e in employees if e["name"] == emp_choice][0]
                    db.add_job(client.strip(), service_id, employee_id, job_date.isoformat(),
                               price_charged, total_cost, status, notes.strip())
                    st.success("Job logged.")
                    st.rerun()

    with st.expander("👥 Manage employees / crew"):
        with st.form("add_employee", clear_on_submit=True):
            e1, e2 = st.columns(2)
            ename = e1.text_input("Name")
            erole = e2.text_input("Role (optional)")
            if st.form_submit_button("Add employee"):
                if ename.strip():
                    db.add_employee(ename.strip(), erole.strip())
                    st.success(f"Added {ename}")
                    st.rerun()
        for e in employees:
            ec1, ec2, ec3 = st.columns([2, 2, 1])
            ec1.write(e["name"])
            ec2.write(e["role"] or "—")
            if ec3.button("🗑️", key=f"delemp_{e['id']}"):
                db.delete_employee(e["id"])
                st.rerun()

    st.markdown("---")
    st.subheader("Job history")

    jobs = db.get_jobs()
    if not jobs:
        st.info("No jobs logged yet.")
        st.stop()

    jobs_df = pd.DataFrame(jobs)

    fc1, fc2, fc3 = st.columns(3)
    status_filter = fc1.multiselect("Filter by status", db.JOB_STATUSES, default=db.JOB_STATUSES)
    service_filter = fc2.multiselect("Filter by service", sorted(jobs_df["service_name"].dropna().unique().tolist()))
    employee_filter = fc3.multiselect("Filter by employee", sorted(jobs_df["employee_name"].dropna().unique().tolist()))

    filtered = jobs_df[jobs_df["status"].isin(status_filter)]
    if service_filter:
        filtered = filtered[filtered["service_name"].isin(service_filter)]
    if employee_filter:
        filtered = filtered[filtered["employee_name"].isin(employee_filter)]

    filtered = filtered.copy()
    filtered["margin"] = filtered["price_charged"] - filtered["total_cost"]

    st.dataframe(
        filtered[["client_name", "service_name", "employee_name", "job_date", "price_charged", "total_cost", "margin", "status", "notes"]],
        width="stretch", hide_index=True,
        column_config={
            "price_charged": st.column_config.NumberColumn("Price", format="$%.2f"),
            "total_cost": st.column_config.NumberColumn("Cost", format="$%.2f"),
            "margin": st.column_config.NumberColumn("Margin", format="$%.2f"),
        },
    )

    del_id = st.selectbox("Delete a job (select by client + date)",
                          ["—"] + [f"{r['client_name']} — {r['job_date']} (id {r['id']})" for _, r in filtered.iterrows()])
    if del_id != "—" and st.button("🗑️ Delete selected job"):
        job_id = int(del_id.split("id ")[1].rstrip(")"))
        db.delete_job(job_id)
        st.rerun()

    st.markdown("---")
    st.subheader("Weekly revenue")
    weekly_df = filtered.copy()
    weekly_df["job_date"] = pd.to_datetime(weekly_df["job_date"], errors="coerce")
    weekly_df = weekly_df.dropna(subset=["job_date"])
    weekly_df = weekly_df[weekly_df["status"].isin(["Completed", "Paid"])]
    if not weekly_df.empty:
        weekly_df["week"] = weekly_df["job_date"].dt.to_period("W").astype(str)
        weekly_rev = weekly_df.groupby("week")["price_charged"].sum()
        st.bar_chart(weekly_rev)
    else:
        st.caption("No completed/paid jobs in the current filter to chart.")


# =============================================================================
# EXPORT
# =============================================================================
elif page == "📤 Export":
    st.title("📤 Export to Excel")

    services = db.get_services()
    competitors = db.get_competitors()
    comp_prices = db.get_competitor_prices()
    jobs = db.get_jobs()
    employees = db.get_employees()

    if not services:
        st.info("Nothing to export yet.")
        st.stop()

    strategy_key = db.get_setting("strategy", "market")

    rows = []
    for s in services:
        stats = sug.compute_competitor_stats(s["id"], comp_prices)
        target = sug.suggested_price(stats, strategy_key)
        status, emoji, message = sug.evaluate_service(s["our_rate"], stats, target)
        rows.append({
            "Service": s["name"],
            "Category": s["category"],
            "Pricing Unit": s["pricing_unit"],
            "Our Rate": s["our_rate"],
            "Market Min": stats["min"] if stats else None,
            "Market Avg": stats["avg"] if stats else None,
            "Market Max": stats["max"] if stats else None,
            "# Competitors": stats["count"] if stats else 0,
            "Suggested Price": target,
            "Status": f"{emoji} {status}",
            "Note": message,
        })
    summary_df = pd.DataFrame(rows)
    services_df = pd.DataFrame(services)
    competitors_df = pd.DataFrame(competitors)
    prices_df = pd.DataFrame(comp_prices)
    jobs_df = pd.DataFrame(jobs)
    employees_df = pd.DataFrame(employees)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="Pricing Summary", index=False)
        services_df.to_excel(writer, sheet_name="Our Services", index=False)
        competitors_df.to_excel(writer, sheet_name="Competitors", index=False)
        prices_df.to_excel(writer, sheet_name="Competitor Prices", index=False)
        jobs_df.to_excel(writer, sheet_name="Job History", index=False)
        employees_df.to_excel(writer, sheet_name="Employees", index=False)
    buffer.seek(0)

    st.download_button(
        "⬇️ Download Excel Workbook",
        data=buffer,
        file_name=f"space_cleaning_report_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    st.markdown("---")
    st.subheader("Preview: Pricing Summary")
    st.dataframe(summary_df, width="stretch", hide_index=True)
