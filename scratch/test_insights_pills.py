from streamlit.testing.v1 import AppTest

def test_insights():
    at = AppTest.from_file("../app.py")
    at.run(timeout=30)

    # 1. Switch to Insights
    at.sidebar.radio[0].set_value("📊 Insights").run(timeout=30)
    print("--- Step 1: Loaded Insights ---")
    print("Subtab in state:", at.session_state["insights_subtab"])
    print("Pills value:", at.pills[0].value)
    titles = [t.value for t in at.markdown if "lux-panel-title" in t.value and not t.value.startswith("<style")]
    print("Rendered panel title:", titles)
    assert any("Fleet Energy Performance" in t for t in titles)

    # 2. Click Charging
    print("\n--- Step 2: Clicking Charging ---")
    at.pills[0].set_value("Charging").run(timeout=30)
    print("Subtab in state:", at.session_state["insights_subtab"])
    print("Pills value:", at.pills[0].value)
    titles = [t.value for t in at.markdown if "lux-panel-title" in t.value and not t.value.startswith("<style")]
    print("Rendered panel title:", titles)
    assert any("Charging Efficiency & Station Distribution" in t for t in titles)
    assert not any("Fleet Energy Performance" in t for t in titles)

    # 3. Click Battery
    print("\n--- Step 3: Clicking Battery ---")
    at.pills[0].set_value("Battery").run(timeout=30)
    print("Subtab in state:", at.session_state["insights_subtab"])
    print("Pills value:", at.pills[0].value)
    titles = [t.value for t in at.markdown if "lux-panel-title" in t.value and not t.value.startswith("<style")]
    print("Rendered panel title:", titles)
    assert any("Battery Trends & Fast-Charging Impact" in t for t in titles)
    assert not any("Charging Efficiency" in t for t in titles)

    # 4. Click Cost
    print("\n--- Step 4: Clicking Cost ---")
    at.pills[0].set_value("Cost").run(timeout=30)
    print("Subtab in state:", at.session_state["insights_subtab"])
    print("Pills value:", at.pills[0].value)
    titles = [t.value for t in at.markdown if "lux-panel-title" in t.value and not t.value.startswith("<style")]
    print("Rendered panel title:", titles)
    assert any("Cost Analysis & Tariff Breakdown" in t for t in titles)
    assert not any("Battery Trends" in t for t in titles)

    # 5. Click Fleet
    print("\n--- Step 5: Clicking Fleet ---")
    at.pills[0].set_value("Fleet").run(timeout=30)
    print("Subtab in state:", at.session_state["insights_subtab"])
    print("Pills value:", at.pills[0].value)
    titles = [t.value for t in at.markdown if "lux-panel-title" in t.value and not t.value.startswith("<style")]
    print("Rendered panel title:", titles)
    assert any("Fleet Energy Performance" in t for t in titles)
    assert not any("Cost Analysis" in t for t in titles)

    # 6. Test External KPI Navigation from Overview
    print("\n--- Step 6: External KPI navigation from Overview ---")
    at.sidebar.radio[0].set_value("🏠 Overview").run(timeout=30)
    btn_energy = [b for b in at.button if b.key == "btn_kpi_energy_act"][0]
    btn_energy.click().run(timeout=30)
    print("After Energy KPI click - Subtab:", at.session_state["insights_subtab"], "Pill:", at.pills[0].value)
    titles = [t.value for t in at.markdown if "lux-panel-title" in t.value and not t.value.startswith("<style")]
    print("Rendered panel title:", titles)
    assert any("Charging Efficiency & Station Distribution" in t for t in titles)

    at.sidebar.radio[0].set_value("🏠 Overview").run(timeout=30)
    btn_cost = [b for b in at.button if b.key == "btn_kpi_cost_act"][0]
    btn_cost.click().run(timeout=30)
    print("After Cost KPI click - Subtab:", at.session_state["insights_subtab"], "Pill:", at.pills[0].value)
    titles = [t.value for t in at.markdown if "lux-panel-title" in t.value and not t.value.startswith("<style")]
    print("Rendered panel title:", titles)
    assert any("Cost Analysis & Tariff Breakdown" in t for t in titles)

    print("\n>>> ALL 4 CATEGORIES AND EXTERNAL HOOKS FULLY VERIFIED! <<<")

if __name__ == "__main__":
    test_insights()
