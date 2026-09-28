"""Build the management-facing competitive workbook from competitive JSON.

The preferred artifact-tool runtime is unavailable in this workspace, so this
script uses the project's existing openpyxl dependency and performs equivalent
structural validation before saving.
"""

from __future__ import annotations

import json
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "output/competitive/restaurants/competitive_analysis_results.json"
OUTPUT = ROOT / "output/competitive/restaurants/competitive_analysis.xlsx"
RESTAURANTS = ["al_assiel", "olivenzweig", "al_safa", "beit_fayrouz"]
DISPLAY = {"al_assiel": "Al Assiel", "olivenzweig": "Olivenzweig", "al_safa": "Al Safa", "beit_fayrouz": "Beit Fayrouz"}

NAVY = "17324D"; TEAL = "0F7C7B"; GOLD = "D6A84B"; PALE = "EAF2F5"; WHITE = "FFFFFF"; GREY = "5B6573"; RED = "F4CCCC"
THIN = Side(style="thin", color="D5DDE5")


def topic(row, name):
    return next((x for x in row if x["internal_topic"] == name), {})


def scalar(value):
    if value is None: return None
    if isinstance(value, (str, int, float, bool)): return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def add_sheet(wb, name, title, subtitle, headers, rows):
    ws = wb.create_sheet(name)
    ws.sheet_view.showGridLines = False
    end = max(1, len(headers))
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=end)
    ws.cell(1, 1, title); ws.cell(1, 1).font = Font(size=18, bold=True, color=WHITE)
    ws.cell(1, 1).fill = PatternFill("solid", fgColor=NAVY); ws.cell(1, 1).alignment = Alignment(vertical="center")
    ws.row_dimensions[1].height = 30
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=end)
    ws.cell(2, 1, subtitle); ws.cell(2, 1).font = Font(size=10, italic=True, color=GREY)
    ws.cell(2, 1).alignment = Alignment(wrap_text=True, vertical="center"); ws.row_dimensions[2].height = 34
    for col, header in enumerate(headers, 1):
        cell = ws.cell(4, col, header); cell.font = Font(bold=True, color=WHITE)
        cell.fill = PatternFill("solid", fgColor=TEAL); cell.alignment = Alignment(wrap_text=True, vertical="center")
    ws.row_dimensions[4].height = 34
    for r_idx, row in enumerate(rows, 5):
        for c_idx, value in enumerate(row, 1):
            cell = ws.cell(r_idx, c_idx, scalar(value)); cell.alignment = Alignment(wrap_text=True, vertical="top")
            cell.border = Border(bottom=THIN)
            if r_idx % 2: cell.fill = PatternFill("solid", fgColor="F7FAFC")
    ws.freeze_panes = "A5"; ws.auto_filter.ref = f"A4:{get_column_letter(end)}{max(4, 4 + len(rows))}"
    for idx, header in enumerate(headers, 1):
        values = [str(ws.cell(r, idx).value or "") for r in range(4, min(ws.max_row, 80) + 1)]
        width = min(max(max(map(len, values), default=10) + 2, 12), 42)
        if any(word in header.lower() for word in ("note", "reason", "source", "url", "conflict", "hours")): width = 42
        ws.column_dimensions[get_column_letter(idx)].width = width
    ws.sheet_properties.pageSetUpPr.fitToPage = True; ws.page_setup.fitToWidth = 1; ws.page_setup.fitToHeight = 0
    ws.print_title_rows = "1:4"
    return ws


def build():
    data = json.loads(INPUT.read_text(encoding="utf-8")); comp = data["restaurant_comparisons"]
    wb = Workbook(); wb.remove(wb.active)
    note = "Formal benchmark cutoff 2026-09-03. All sample sizes remain visible; observed leaders require configured minimum evidence."
    headers = ["Restaurant", "Recent 90d reviews", "Avg rating", "5-star share %", "1–2-star share %", "Written share %", "Owner response %", "Bad-review response %", "Food positive %", "Service positive %", "Value positive %"]
    rows = []
    for slug in RESTAURANTS:
        r = comp[slug]["periods"]["recent_90d"]; ts = comp[slug]["recent_90d_topics"]
        rows.append([DISPLAY[slug], r["review_count"], r["average_rating"], r["five_star_share_pct"], r["low_score_share_pct"], r["written_review_share_pct"], r["owner_response_rate_pct"], r["bad_review_response_rate_pct"], topic(ts, "Food").get("positive_share_pct"), topic(ts, "Service").get("positive_share_pct"), topic(ts, "Price & Value").get("positive_share_pct")])
    ws = add_sheet(wb, "Executive Benchmark", "Executive Competitive Benchmark", note, headers, rows)
    ws.conditional_formatting.add(f"C5:C{ws.max_row}", ColorScaleRule(start_type="min", start_color=RED, end_type="max", end_color="63BE7B"))
    chart = BarChart(); chart.title = "Recent 90-Day Rating"; chart.y_axis.title = "Rating"; chart.height = 7; chart.width = 12
    chart.add_data(Reference(ws, min_col=3, min_row=4, max_row=8), titles_from_data=True); chart.set_categories(Reference(ws, min_col=1, min_row=5, max_row=8)); ws.add_chart(chart, "M4")
    leader_rows = [[key.replace("_", " ").title(), DISPLAY.get(value.get("leader"), value.get("leader")), value.get("value"), value.get("sample_size") or value.get("mentions"), value.get("note")] for key, value in data["observed_leaders"].items()]
    start = 11; ws.cell(start, 1, "Observed leaders / evidence gates").font = Font(bold=True, color=WHITE); ws.cell(start,1).fill=PatternFill("solid",fgColor=GOLD)
    leader_headers = ["Metric", "Observed leader", "Value", "Evidence sample", "Qualification note"]
    for j, value in enumerate(leader_headers, 1):
        ws.cell(start + 1, j, value); ws.cell(start + 1, j).font = Font(bold=True, color=WHITE); ws.cell(start + 1, j).fill = PatternFill("solid", fgColor=TEAL)
    for i,row in enumerate(leader_rows,start+2):
        for j,v in enumerate(row,1): ws.cell(i,j,scalar(v))
    ws.column_dimensions["A"].width = 42; ws.column_dimensions["B"].width = 22
    ws.column_dimensions["C"].width = 18; ws.column_dimensions["D"].width = 18; ws.column_dimensions["E"].width = 34

    for period, sheet_name, title in (("recent_90d","90-Day Comparison","Common Recent 90-Day Comparison"),("latest_30d","30-Day Comparison","Common Latest 30-Day Comparison")):
        hs = ["Restaurant","Start","End","Reviews","Reviews/week","Average rating","5-star %","1–2-star %","Written reviews","Written %","Responses %","Bad-review response %","Unanswered low-score","Evidence"]
        rs=[]
        for slug in RESTAURANTS:
            r=comp[slug]["periods"][period]
            rs.append([DISPLAY[slug],r["start"],r["end"],r["review_count"],r["reviews_per_week"],r["average_rating"],r["five_star_share_pct"],r["low_score_share_pct"],r["written_reviews"],r["written_review_share_pct"],r["owner_response_rate_pct"],r["bad_review_response_rate_pct"],r["unanswered_low_score_count"],r["evidence_level"]])
        add_sheet(wb,sheet_name,title,note,hs,rs)

    hs=["Restaurant","Recent avg","Previous avg","Historical avg","Recent vs previous","Recent vs historical","Recent low-score %","Previous low-score %","Historical low-score %","Recent review count","Previous review count","Count change"]
    rs=[]
    for slug in RESTAURANTS:
        p=comp[slug]["periods"]; t=comp[slug]["trend"]
        rs.append([DISPLAY[slug],p["recent_90d"]["average_rating"],p["previous_90d"]["average_rating"],p["historical"]["average_rating"],t["recent_90d_vs_previous_90d"]["average_rating_change"],t["recent_90d_vs_historical"]["average_rating_change"],p["recent_90d"]["low_score_share_pct"],p["previous_90d"]["low_score_share_pct"],p["historical"]["low_score_share_pct"],p["recent_90d"]["review_count"],p["previous_90d"]["review_count"],t["recent_90d_vs_previous_90d"]["review_count_change"]])
    add_sheet(wb,"Rating Trends","Rating Trend Benchmark","Exact common windows; historical ends 2026-03-07.",hs,rs)

    hs=["Restaurant","Period","Start","End","Reviews","Reviews/week","Evidence"]
    rs=[]
    for slug in RESTAURANTS:
        for name in ("latest_30d","previous_30d","recent_90d","previous_90d","historical"):
            r=comp[slug]["periods"][name]; rs.append([DISPLAY[slug],name,r["start"],r["end"],r["review_count"],r["reviews_per_week"],r["evidence_level"]])
    add_sheet(wb,"Review Cadence","Review Cadence",note,hs,rs)

    hs=["Restaurant","Scope","Reviews","Responses","Response %","Low-score reviews","Low-score responses","Bad-review response %","Unanswered low-score","Median delay days","Delay sample"]
    rs=[]
    for slug in RESTAURANTS:
        overall=data["owner_response_benchmark"][slug]["overall_from_layer_05"]; recent=comp[slug]["periods"]["recent_90d"]
        rs.append([DISPLAY[slug],"all collected (Layer 05)",overall["total_reviews"],overall["reviews_with_owner_response"],overall["owner_response_rate_pct"],None,None,None,None,None,None])
        rs.append([DISPLAY[slug],"common recent 90d",recent["review_count"],recent["owner_responses"],recent["owner_response_rate_pct"],recent["low_score_count"],recent["low_score_responses"],recent["bad_review_response_rate_pct"],recent["unanswered_low_score_count"],recent["median_response_delay_days"],recent["response_delays_with_data"]])
    add_sheet(wb,"Owner Responses","Owner Response Benchmark","Response-delay metrics remain blank where Google supplied no valid response timestamp.",hs,rs)

    hs=["Restaurant","Low-score count","Share % through cutoff","Evidence","Owner response %","Unanswered","Top issue 1","Count","Share of written low-score %","Issue evidence","Top issue 2","Count 2"]
    rs=[]
    for slug in RESTAURANTS:
        low=comp[slug]["low_score_comparison"]; top=low["top_negative_topics"]
        a=top[0] if top else {}; b=top[1] if len(top)>1 else {}
        rs.append([DISPLAY[slug],low["count"],low["share_pct"],low["evidence_level"],low["owner_response_rate_pct"],low["unanswered_count"],a.get("topic"),a.get("count"),a.get("share_of_written_reviews_pct"),a.get("evidence_level"),b.get("topic"),b.get("count")])
    add_sheet(wb,"Low-Score Comparison","Low-Score Cause Comparison","1–2-star reviews through common cutoff; topic percentages use written low-score reviews.",hs,rs)

    hs=["Restaurant","Topic","Mentions","Share of written %","Positive","Positive %","Negative","Negative %","Neutral","Avg whole-review rating","Evidence","Positive evidence","Negative evidence"]
    rs=[]
    for slug in RESTAURANTS:
        for x in comp[slug]["recent_90d_topics"]: rs.append([DISPLAY[slug],x["topic"],x["count"],x["share_of_written_reviews_pct"],x["positive_count"],x["positive_share_pct"],x["negative_count"],x["negative_share_pct"],x["neutral_count"],x["average_whole_review_rating"],x["evidence_level"],x["positive_evidence_level"],x["negative_evidence_level"]])
    add_sheet(wb,"Topic Comparison","Recent 90-Day Topic Comparison","Identical aliases/definitions; zero support is evidence 'none'.",hs,rs)
    filtered=[row for row in rs if row[1] in {"Food","Taste","Food Quality","Food Variety","Freshness","Food Temperature","Food Presentation","Meat Quality","Portion Size","Authenticity","Service","Staff Friendliness","Staff Attentiveness","Staff Professionalism","Staff Communication","Waiting Time","Hospitality"}]
    add_sheet(wb,"Food & Service","Food and Service Detail",note,hs,filtered)

    hs=["Restaurant","Drink topic mentions","Drink share of written %","Positive","Negative","Recent sentiment evidence","Food topic mentions","Food positive %","Food menu items","Drink menu items","Mocktail items","Signature drinks","Guardrail"]
    rs=[]
    for slug in RESTAURANTS:
        kb=data["kitchen_bar_comparison"][slug]; dr=kb["drink_review_attention"] or {}; food=kb["food_review_attention"] or {}
        rs.append([DISPLAY[slug],dr.get("count"),dr.get("share_of_written_reviews_pct"),dr.get("positive_count"),dr.get("negative_count"),dr.get("evidence_level"),food.get("count"),food.get("positive_share_pct"),kb["food_menu_size"],kb["drink_menu_size"],kb["mocktail_program_item_count"],", ".join(kb["signature_drinks"]),kb["guardrail"]])
    add_sheet(wb,"Drinks - Bar","Kitchen / Bar Review-Attention Comparison","Review attention is not sales or revenue.",hs,rs)

    hs=["Restaurant","Menu items","Categories","Priced items","Price coverage %","Starters","Salads","Grill / Meat Mains","Other Main Dishes","Breakfast","Brunch","Desserts","Drinks / Bar","Sharing Platters","Sandwiches","Vegetarian / Vegan","Specials","Vegetarian status","Family-bundle status","Buffet status","Shisha status","Catering status","Events status"]
    rs=[]
    for slug in RESTAURANTS:
        m=data["menu_comparison"][slug]; g=m["normalized_comparison_groups"]; a=m["availability"]
        rs.append([DISPLAY[slug],m["menu_item_count"],m["category_count"],m["priced_items"],m["price_coverage_pct"],g["Starters"]["item_count"],g["Salads"]["item_count"],g["Grill / Meat Mains"]["item_count"],g["Other Main Dishes"]["item_count"],g["Breakfast"]["item_count"],g["Brunch"]["item_count"],g["Desserts"]["item_count"],g["Drinks / Bar"]["item_count"],g["Sharing Platters"]["item_count"],g["Sandwiches"]["item_count"],g["Vegetarian / Vegan"]["item_count"],g["Specials"]["item_count"],a["vegetarian_vegan"],a["family_bundles"],a["buffet"],a["shisha"],a["catering"],a["events"]])
    add_sheet(wb,"Menu Comparison","Normalized Menu Comparison","Counts are source-aware September 2026 snapshots; Al Safa is explicitly partial.",hs,rs)

    hs=["Restaurant","Original category","Captured item count"]
    rs=[]
    for slug in RESTAURANTS:
        for category,count in data["menu_comparison"][slug]["original_category_counts"].items():
            rs.append([DISPLAY[slug],category,count])
    add_sheet(wb,"Original Categories","Original Menu Categories","Source category labels are preserved separately from non-exclusive normalized comparison groups.",hs,rs)

    p=data["comparable_price_basket"]
    add_sheet(wb,"Comparable Prices","Comparable Price Basket","Only reasonable matches are included; confidence and source/date remain visible.",["Comparison item","Restaurant","Matched item","Price","Currency","Source","Source date","Match confidence","Notes"],[[x["comparison_item"],DISPLAY[x["restaurant"]],x["matched_item"],x["price"],x["currency"],x["source"],x["source_date"],x["match_confidence"],x["notes"]] for x in p])

    hs=["Restaurant","Signal type","Dish","Category","Price EUR","Reviews mentioning","Positive reviews","Negative reviews","Evidence"]
    rs=[]
    for slug in RESTAURANTS:
        block=data["dish_favourite_signals"][slug]
        for key in ("most_discussed","most_positively_discussed","negatively_discussed"):
            for x in block[key]: rs.append([DISPLAY[slug],key,x.get("dish"),x.get("category"),x.get("price_eur"),x.get("reviews_mentioning"),x.get("positive_reviews"),x.get("negative_reviews"),x.get("evidence_level")])
    add_sheet(wb,"Dishes","Dish / Favourite Signals","Google review attention only; no best-seller or order-volume claim.",hs,rs)

    hs=["Restaurant","Dish","Reason selected","Google mentions","Positive","Positive share %","Negative","Recent mentions","Platform signal","Menu price","Currency","Evidence","Interpretation"]
    rs=[]
    for slug in RESTAURANTS:
        for x in data["competitor_tasting_shortlist"][slug]: rs.append([DISPLAY[slug],x["dish"],x["reason_selected"],x["google_review_mentions"],x["positive_mentions"],x["positive_share_pct"],x["negative_mentions"],x["recent_mentions"],x["platform_signal"],x["menu_price"],x["currency"],x["evidence_level"],x["interpretation"]])
    add_sheet(wb,"Tasting Shortlist","Competitor Tasting Shortlist","Field-research candidates; platform signals remain separate from Google sentiment.",hs,rs)

    hs=["Restaurant","Website","Google presence","Online reservation","Delivery","Takeaway","Catering","Events","Parking","Outdoor seating","Bar/drinks","Shisha","Opening hours","Menu URLs"]
    rs=[]
    for slug in RESTAURANTS:
        f=data["digital_service_footprint"][slug]; rs.append([DISPLAY[slug],f["official_website"],f["google_presence"],f["online_reservation"],f["delivery"],f["takeaway"],f["catering"],f["events"],f["parking"],f["outdoor_seating"],f["bar_drinks"],f["shisha"],f["opening_hours"],f["menu_urls"]])
    add_sheet(wb,"Digital Footprint","Digital / Service Footprint","Unknown fields remain blank/null rather than inferred.",hs,rs)

    hs=["Restaurant","Source name","Type","URL","Retrieved","Used for","Confidence","Notes","Conflicts"]
    rs=[]
    for slug in RESTAURANTS:
        for x in data["source_registers"][slug]["sources"]: rs.append([DISPLAY[slug],x.get("source_name"),x.get("source_type"),x.get("url"),x.get("retrieved_at"),x.get("used_for"),x.get("confidence"),x.get("notes"),x.get("conflicts")])
    add_sheet(wb,"Source Register","Source Register","Authority, retrieval dates, and conflicts are preserved; the supplied PDF is supporting evidence.",hs,rs)

    hs=["Restaurant","Reviews collected","Written reviews","Earliest","Latest","Known language","English written","Non-English written","Translated non-English","Translation coverage %","Usable text","Usable coverage %","Duplicate IDs","Invalid records","Menu items","Priced items","Menu completeness","Profile source quality"]
    rs=[]
    for slug in RESTAURANTS:
        q=data["data_quality"][slug]; rs.append([DISPLAY[slug],q["reviews_collected"],q["written_reviews"],q["earliest_review_date"],q["latest_review_date"],q["language_coverage_known_count"],q["english_written_reviews"],q["non_english_written_reviews"],q["translated_non_english_reviews"],q["non_english_translation_coverage_pct"],q["usable_analysis_text_reviews"],q["usable_analysis_text_coverage_pct"],q["duplicate_review_ids"],q["invalid_records"],q["menu_items"],q["menu_priced_items"],q["menu_source_completeness"],q["profile_source_quality"]])
    add_sheet(wb,"Data Quality","Data Quality and Comparability","Differences in data volume and menu/source completeness must remain visible in interpretation.",hs,rs)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True); wb.save(OUTPUT)
    check=load_workbook(OUTPUT,data_only=False)
    errors=[]
    for ws in check.worksheets:
        if ws.max_row < 4 or ws.max_column < 1: errors.append(f"{ws.title}: empty")
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value,str) and cell.value.startswith(("#REF!","#DIV/0!","#VALUE!","#NAME?","#N/A")): errors.append(f"{ws.title}!{cell.coordinate}: {cell.value}")
    if errors: raise RuntimeError("Workbook validation failed: "+"; ".join(errors))
    print(f"Workbook: {OUTPUT}")
    print(f"Sheets: {len(check.sheetnames)}")
    print("Validation: no empty sheets or obvious formula/error values")


if __name__ == "__main__": build()
