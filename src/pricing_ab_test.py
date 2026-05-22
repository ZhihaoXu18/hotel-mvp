# pricing_ab_test.py

import pandas as pd
import numpy as np
from scipy import stats
import json

# 1. 读入实验数据 / 或先手动构造
# 2. 分成 control / treatment
# 3. 比较 revenue
# 4. 做统计检验
# 5. 输出结果

def simulate_ab_data(control_mean, treatment_mean, std=5000, n=30, seed=42):
    np.random.seed(seed)

    control = np.random.normal(loc=control_mean, scale=std, size=n)
    treatment = np.random.normal(loc=treatment_mean, scale=std, size=n)

    return control, treatment

def compare_means(control, treatment):
    control_mean = np.mean(control)
    treatment_mean = np.mean(treatment)
    uplift_pct = (treatment_mean - control_mean) / control_mean * 100

    return control_mean, treatment_mean, uplift_pct

def run_ttest(control, treatment):
    t_stat, p_value = stats.ttest_ind(treatment, control, equal_var=False)
    return t_stat, p_value

def make_decision(uplift_pct, p_value, alpha=0.05):
    if p_value < alpha and uplift_pct > 0:
        return "Deploy new pricing"
    elif p_value < alpha and uplift_pct <= 0:
        return "Do NOT deploy"
    else:
        return "Inconclusive - need more data"
    
def run_scenario_ab_test_for_row(row, seed=100):
    control, treatment = simulate_ab_data(
        control_mean=row["mid_revenue"],
        treatment_mean=row["high_revenue"],
        seed=seed
    )

    control_mean, treatment_mean, uplift_pct = compare_means(control, treatment)
    t_stat, p_value = run_ttest(control, treatment)
    decision = make_decision(uplift_pct, p_value)

    return {
        "category": row["category"],
        "price_tier": row["price_tier"],
        "control_revenue": control_mean,
        "treatment_revenue": treatment_mean,
        "uplift_pct": uplift_pct,
        "p_value": p_value,
        "decision": decision
    }

if __name__ == "__main__":
    input_path = "/Users/zhihaoxu/Desktop/Project:Code/hotel-mvp/data_out/ab_test_input.csv"
    optimization_input = pd.read_csv(input_path)

    scenario_input_path = "/Users/zhihaoxu/Desktop/Project:Code/hotel-mvp/data_out/scenario_ab_input.csv"
    scenario_input = pd.read_csv(scenario_input_path)

    all_results = []
    scenario_ab_results = []

    # A/B test for all optimization groups
    for i, row in optimization_input.iterrows():
        control, treatment = simulate_ab_data(
            control_mean=row["baseline_revenue"],
            treatment_mean=row["optimal_revenue"],
            seed=42 + i
        )

        control_mean, treatment_mean, uplift_pct = compare_means(control, treatment)
        t_stat, p_value = run_ttest(control, treatment)
        decision = make_decision(uplift_pct, p_value)

        all_results.append({
            "category": row["category"],
            "baseline_revenue": control_mean,
            "optimal_price": row["optimal_price"],
            "treatment_revenue": treatment_mean,
            "uplift_pct": uplift_pct,
            "p_value": p_value,
            "decision": decision
        })

    # A/B test for scenario groups
    for i, row in scenario_input.iterrows():
        result = run_scenario_ab_test_for_row(row, seed=100 + i)
        if result is not None:
            scenario_ab_results.append(result)

    scenario_ab_results_df = pd.DataFrame(scenario_ab_results)
    ab_results_df = pd.DataFrame(all_results)

    print("\n" + "=" * 100)
    print("A/B TEST RESULTS FOR SCENARIO GROUPS")
    print("=" * 100)
    if not scenario_ab_results_df.empty:
        print(scenario_ab_results_df.round(2).to_string(index=False))
    else:
        print("No scenario groups selected for A/B testing.")

    print("\n" + "=" * 100)
    print("A/B TEST RESULTS FOR ALL OPTIMIZATION GROUPS")
    print("=" * 100)
    if not ab_results_df.empty:
        print(ab_results_df.round(2).to_string(index=False))
    else:
        print("No optimization groups selected for A/B testing.")

        # Save optimization A/B results as JSON
    optimization_ab_json = ab_results_df.round(2).to_dict(orient="records")
    optimization_ab_json_path = "/Users/zhihaoxu/Desktop/Project:Code/hotel-mvp/data_out/optimization_ab_results.json"

    with open(optimization_ab_json_path, "w", encoding="utf-8") as f:
        json.dump(optimization_ab_json, f, indent=4, ensure_ascii=False, default=str)

    print("\nOptimization A/B JSON file saved:")
    print(optimization_ab_json_path)

    # Save scenario A/B results as JSON
    scenario_ab_json = scenario_ab_results_df.round(2).to_dict(orient="records")
    scenario_ab_json_path = "/Users/zhihaoxu/Desktop/Project:Code/hotel-mvp/data_out/scenario_ab_results.json"

    with open(scenario_ab_json_path, "w", encoding="utf-8") as f:
        json.dump(scenario_ab_json, f, indent=4, ensure_ascii=False, default=str)

    print("\nScenario A/B JSON file saved:")
    print(scenario_ab_json_path)