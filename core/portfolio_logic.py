# core/portfolio_logic.py
import uuid
from datetime import datetime
# pandas is not strictly needed here for this specific function

def prepare_new_portfolio_data_for_gsheet(
    # Basic Info
    form_new_portfolio_name_in_form: str,
    selected_program_type_to_use_in_form: str,
    form_new_initial_balance_in_form: float,
    form_new_status_in_form: str,
    form_new_evaluation_step_val_in_form: str,
    form_notes_val: str,

    # Prop Firm / Funded Account Rules
    form_profit_target_val: float,
    form_daily_loss_val: float,
    form_total_stopout_val: float,
    form_leverage_val: float,
    form_min_days_val: int,

    # Trading Competition Rules
    form_comp_end_date, # date object or None
    form_comp_goal_metric: str,
    form_profit_target_val_comp: float,
    form_daily_loss_val_comp: float,
    form_total_stopout_val_comp: float,

    # Personal Account Goals
    form_pers_overall_profit_val: float,
    form_pers_target_end_date, # date object or None
    form_pers_weekly_profit_val: float,
    form_pers_daily_profit_val: float,
    form_pers_max_dd_overall_val: float,
    form_pers_max_dd_daily_val: float,

    # Scaling Manager Settings
    form_enable_scaling_checkbox_val: bool,
    form_scaling_freq_val: str,
    form_su_wr_val: float,
    form_su_gain_val: float,
    form_su_inc_val: float,
    form_sd_loss_val: float,
    form_sd_wr_val: float,
    form_sd_dec_val: float,
    form_min_risk_val: float,
    form_max_risk_val: float,
    form_current_risk_val: float,
    account_type_in_form: str # <<<< จุดที่ 2: เพิ่ม 'account_type_in_form: str' ตรงนี้
):
    new_id_value = str(uuid.uuid4())
    creation_date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    data_to_save = {
        'PortfolioID': new_id_value,
        'PortfolioName': form_new_portfolio_name_in_form,
        'ProgramType': selected_program_type_to_use_in_form,
        'EvaluationStep': form_new_evaluation_step_val_in_form if selected_program_type_to_use_in_form == "Prop Firm Challenge" else "",
        'Status': form_new_status_in_form,
        'InitialBalance': form_new_initial_balance_in_form,
        'CreationDate': creation_date_str,
        'Notes': form_notes_val,
        'AccountID': '', # <--- AccountID มีอยู่แล้ว
        'AccountType': account_type_in_form # <<<< จุดที่ 3: เพิ่ม 'AccountType' เข้าไปใน Dictionary
    }

    if selected_program_type_to_use_in_form in ["Prop Firm Challenge", "Funded Account"]:
        data_to_save.update({
            'ProfitTargetPercent': form_profit_target_val,
            'DailyLossLimitPercent': form_daily_loss_val,
            'TotalStopoutPercent': form_total_stopout_val,
            'Leverage': form_leverage_val,
            'MinTradingDays': form_min_days_val
        })

    if selected_program_type_to_use_in_form == "Trading Competition":
        data_to_save.update({
            'CompetitionEndDate': form_comp_end_date.strftime("%Y-%m-%d") if form_comp_end_date else None,
            'CompetitionGoalMetric': form_comp_goal_metric,
            'ProfitTargetPercent': form_profit_target_val_comp,
            'DailyLossLimitPercent': form_daily_loss_val_comp,
            'TotalStopoutPercent': form_total_stopout_val_comp
        })

    if selected_program_type_to_use_in_form == "Personal Account":
        data_to_save.update({
            'OverallProfitTarget': form_pers_overall_profit_val,
            'TargetEndDate': form_pers_target_end_date.strftime("%Y-%m-%d") if form_pers_target_end_date else None,
            'WeeklyProfitTarget': form_pers_weekly_profit_val,
            'DailyProfitTarget': form_pers_daily_profit_val,
            'MaxAcceptableDrawdownOverall': form_pers_max_dd_overall_val,
            'MaxAcceptableDrawdownDaily': form_pers_max_dd_daily_val
        })

    # --- SCALING MANAGER DATA ---
    # Always include scaling fields, using defaults from ui/portfolio_section.py
    # if not explicitly enabled or changed by user.
    data_to_save['EnableScaling'] = form_enable_scaling_checkbox_val
    data_to_save['ScalingCheckFrequency'] = form_scaling_freq_val
    data_to_save['ScaleUp_MinWinRate'] = form_su_wr_val
    data_to_save['ScaleUp_MinGainPercent'] = form_su_gain_val
    data_to_save['ScaleUp_RiskIncrementPercent'] = form_su_inc_val
    data_to_save['ScaleDown_MaxLossPercent'] = form_sd_loss_val
    data_to_save['ScaleDown_LowWinRate'] = form_sd_wr_val
    data_to_save['ScaleDown_RiskDecrementPercent'] = form_sd_dec_val
    data_to_save['MinRiskPercentAllowed'] = form_min_risk_val   # This will now have a sensible default
    data_to_save['MaxRiskPercentAllowed'] = form_max_risk_val   # This will now have a sensible default
    data_to_save['CurrentRiskPercent'] = form_current_risk_val # This will now have a sensible default

    return data_to_save