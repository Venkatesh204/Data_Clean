# -*- coding: utf-8 -*-
"""
Data Cleaner Pro - A Gradio Application for Cleaning Tabular Data
"""

import sys
import subprocess
import importlib.metadata
import warnings
import os
import io
import base64
import re
import traceback
from pathlib import Path

# --- Suppress Warnings ---
warnings.simplefilter("ignore", category=UserWarning)
warnings.simplefilter("ignore", category=FutureWarning)

# --- Global Variables & Constants ---
REQUIRED_LIBRARIES = {
    'pandas',
    'gradio',
    'openpyxl',
    'matplotlib',
    'numpy'
}
CSS_FILE_PATH = Path(__file__).parent / "style.css" # Path relative to script

# --- Library Check Function ---
def check_libraries():
    """Checks if required libraries are installed."""
    print("--- Library Check ---")
    missing = []
    for lib in REQUIRED_LIBRARIES:
        try:
            version = importlib.metadata.version(lib)
            print(f"  ✅ {lib} ({version})")
        except importlib.metadata.PackageNotFoundError:
            print(f"  ❌ {lib}: Not Found.")
            missing.append(lib)
        except Exception as e:
            print(f"  ⚠️ {lib}: Error during check - {e}")
            missing.append(lib) # Add to list just in case

    if missing:
        print("\n--- MISSING LIBRARIES ---")
        print(f"The following required libraries are missing: {', '.join(sorted(missing))}")
        print("Please install them using pip:")
        print(f"  pip install {' '.join(sorted(missing))}")
        print("Alternatively, install all requirements:")
        print(f"  pip install -r requirements.txt")
        print("--------------------------")
        return False
    else:
        print("\nAll required libraries are installed.")
        print("--------------------------")
        return True

# --- Import Core Libraries (Conditional) ---
libraries_ready = check_libraries()

if libraries_ready:
    import pandas as pd
    import numpy as np
    import gradio as gr
    import matplotlib
    # Set backend *before* importing pyplot
    try:
        matplotlib.use('Agg')
        print(f"Matplotlib backend set to: {matplotlib.get_backend()}")
    except Exception as e:
        print(f"Warning: Could not set Matplotlib backend. Using default. Error: {e}")
    import matplotlib.pyplot as plt
else:
    print("\nERROR: Required libraries are missing. Please install them and restart the script.")
    # Exit if libraries are absolutely essential for the script to even load
    sys.exit(1) # Exit the script if core libs like pandas/gradio are missing

# --- Backend Logic (Functions from previous Cell 3) ---

# --- Hardcoded Cleaning Rules ---
DEFAULT_CLEANING_RULES = [
    {"keywords": ["email"], "comment": "Keep typical email chars", "remove_chars_regex": r'[^a-zA-Z0-9@._-]'},
    {"keywords": ["phone", "mobile", "number"], "comment": "Keep only digits", "remove_chars_regex": r'[^\d]'},
    {"keywords": ["name", "address", "company", "organization", "person", "city", "state", "country"], "comment": "Keep letters, numbers, space, .,-()/", "remove_chars_regex": r'[^\w\s.,\-()\/]'}
]

# --- load_data function ---
def load_data(file_obj):
    """Loads data from CSV or XLSX file object."""
    if file_obj is None:
        return ( None, [], None, gr.update(choices=[], value=[], interactive=False), gr.update(value=None, visible=False), gr.update(value="Status: No file uploaded. Please upload a CSV or XLSX file.", visible=True), gr.update(value="", visible=False), gr.update(value=create_dummy_plot("Upload Data to View Plot"), visible=True) )
    try:
        file_path = Path(file_obj.name); file_extension = file_path.suffix.lower()
        print(f"Attempting to load file: {file_path.name}")
        if file_extension == '.csv':
            try: df = pd.read_csv(file_path)
            except UnicodeDecodeError: df = pd.read_csv(file_path, encoding='latin1')
            except Exception as csv_e: raise ValueError(f"Error reading CSV: {csv_e}") from csv_e
        elif file_extension in ['.xlsx', '.xls']:
             try: df = pd.read_excel(file_path)
             except Exception as excel_e: raise ValueError(f"Error reading Excel: {excel_e}") from excel_e
        else: raise ValueError(f"Unsupported file type: '{file_extension}'. Please upload CSV or XLSX.")
        print(f"Successfully loaded {len(df)} rows and {len(df.columns)} columns.")
        df.columns = [str(col) for col in df.columns]
        columns = df.columns.tolist()
        preview_df = df.head()
        return ( df, columns, preview_df, gr.update(choices=columns, value=columns, interactive=True), gr.update(value=preview_df, visible=True), gr.update(value="✅ File loaded successfully. Review profile/plots below and configure cleaning in Tab 2.", visible=True), gr.update(value="", visible=False), gr.update(value=None, visible=False) )
    except Exception as e:
        print(f"ERROR in load_data: {e}"); traceback.print_exc()
        error_message = f"❌ Error loading file: {e}. Please check the file format and integrity."
        return ( None, [], None, gr.update(choices=[], value=[], interactive=False), gr.update(value=None, visible=False), gr.update(value=error_message, visible=True), gr.update(value="", visible=False), gr.update(value=create_dummy_plot("File Load Error"), visible=True) )

# --- Helper: Create a Dummy Plot ---
def create_dummy_plot(message="Plot Failed or No Data"):
    """Creates a simple placeholder plot with a text message."""
    try:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.text(0.5, 0.5, message, horizontalalignment='center', verticalalignment='center', fontsize=10, color='grey', wrap=True, ha='center', va='center')
        ax.set_xticks([]); ax.set_yticks([])
        ax.spines[['top', 'right', 'bottom', 'left']].set_visible(False)
        fig.patch.set_facecolor('#f8f9fa'); ax.set_facecolor('#f8f9fa')
        plt.tight_layout(); return fig
    except Exception as e:
        print(f"!!! ERROR creating dummy plot: {e}"); traceback.print_exc(); return None

# --- generate_basic_plots function ---
def generate_basic_plots(df, plot_prefix="Initial"):
    """Generates basic histogram and bar chart for the dataframe."""
    num_plot = None; cat_plot = None; plot_messages = []
    if df is None or df.empty:
        plot_messages.append("No data available.")
        num_plot = create_dummy_plot(f"{plot_prefix}\nNo Numeric Data"); cat_plot = create_dummy_plot(f"{plot_prefix}\nNo Categorical Data")
        return num_plot, cat_plot, plot_messages
    numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
    # Histogram
    if numeric_cols:
        num_col = numeric_cols[0]
        try:
            plot_data = df[num_col].replace([np.inf, -np.inf], np.nan).dropna()
            if not plot_data.empty and pd.api.types.is_numeric_dtype(plot_data): # is_numeric_dtype is fine
                fig_num, ax_num = plt.subplots(figsize=(6, 4))
                plot_data.plot(kind='hist', ax=ax_num, bins=30, color='#007bff', alpha=0.7)
                ax_num.set_title(f'{plot_prefix} Dist: {num_col}', fontsize=10); ax_num.tick_params(axis='both', which='major', labelsize=8)
                ax_num.set_xlabel(num_col, fontsize=9); ax_num.set_ylabel('Frequency', fontsize=9)
                ax_num.grid(axis='y', linestyle='--', alpha=0.6); plt.tight_layout(); num_plot = fig_num; plt.close(fig_num)
                plot_messages.append(f"Histogram: '{num_col}' OK.")
            else: plot_messages.append(f"No valid data for histogram '{num_col}'."); num_plot = create_dummy_plot(f"{plot_prefix} Histogram\nNo Valid Data\n({num_col})")
        except Exception as e: print(f"!!! ERROR generating {plot_prefix} histogram for {num_col}: {e}"); plot_messages.append(f"Failed histogram '{num_col}'."); num_plot = create_dummy_plot(f"{plot_prefix} Histogram\nError\n({num_col})")
    else: plot_messages.append("No numerical cols."); num_plot = create_dummy_plot(f"{plot_prefix}\nNo Numeric Columns")
    # Bar chart
    cat_col_to_plot = None
    if categorical_cols:
        suitable_cols = []
        for col in categorical_cols:
            try: nunique = df[col].astype(str).nunique();
            if 1 < nunique <= 30: suitable_cols.append((nunique, col))
            except Exception: continue
        if suitable_cols: cat_col_to_plot = sorted(suitable_cols)[0][1]
        elif categorical_cols:
            for col in categorical_cols:
                try:
                    if df[col].astype(str).nunique() > 1: cat_col_to_plot = col; break
                except Exception: continue
    if cat_col_to_plot:
        try:
            counts = df[cat_col_to_plot].astype(str).value_counts().nlargest(20).sort_values()
            if not counts.empty:
                fig_height = max(4, len(counts) * 0.3 + 1); fig_cat, ax_cat = plt.subplots(figsize=(7, fig_height))
                counts.plot(kind='barh', ax=ax_cat, color='#fd7e14', alpha=0.8)
                ax_cat.set_title(f'{plot_prefix} Counts: {cat_col_to_plot} (Top {len(counts)})', fontsize=10); ax_cat.tick_params(axis='both', which='major', labelsize=8)
                ax_cat.set_xlabel('Count', fontsize=9); ax_cat.set_ylabel(cat_col_to_plot, fontsize=9)
                ax_cat.grid(axis='x', linestyle='--', alpha=0.6); plt.tight_layout(); cat_plot = fig_cat; plt.close(fig_cat)
                plot_messages.append(f"Bar chart: '{cat_col_to_plot}' OK.")
            else: plot_messages.append(f"No counts for bar chart '{cat_col_to_plot}'."); cat_plot = create_dummy_plot(f"{plot_prefix} Bar Chart\nNo Counts\n({cat_col_to_plot})")
        except Exception as e: print(f"!!! ERROR generating {plot_prefix} bar chart for {cat_col_to_plot}: {e}"); plot_messages.append(f"Failed bar chart '{cat_col_to_plot}'."); cat_plot = create_dummy_plot(f"{plot_prefix} Bar Chart\nError\n({cat_col_to_plot})")
    else: plot_messages.append("No suitable cat cols."); cat_plot = create_dummy_plot(f"{plot_prefix}\nNo Suitable\nCategorical Columns")
    return num_plot, cat_plot, plot_messages

# --- handle_file_upload function ---
def handle_file_upload(file_obj):
    """ Calls load_data, generates profile & plots, prepares updates."""
    print("\n--- handle_file_upload triggered ---")
    reset_defaults = reset_all()
    load_result = load_data(file_obj)
    df, columns, preview_df, dd_update_ph, pv_update_ph, status_update_ph, profile_update_ph, null_plot_update_ph = load_result
    profile_md = ""; null_plot_object = None; initial_num_plot = None; initial_cat_plot = None
    date_col_update = gr.update(choices=[], value=[], interactive=False)
    dd_update = dd_update_ph; pv_update = pv_update_ph
    status_update_dict_from_load = status_update_ph
    initial_status_message = "Status: Processing..."; initial_status_visible = True
    if isinstance(status_update_dict_from_load, dict):
        initial_status_message = status_update_dict_from_load.get('value', initial_status_message)
        initial_status_visible = status_update_dict_from_load.get('visible', initial_status_visible)
    elif status_update_dict_from_load is None: initial_status_message = "Status: Error during load."
    final_status_update = gr.update(value=initial_status_message, visible=initial_status_visible)
    if df is not None and not df.empty:
        print("File loaded, generating initial profile and plots...")
        date_col_update = gr.update(choices=columns, value=[], interactive=True)
        try: # Profile
            profile_buffer = io.StringIO()
            profile_buffer.write(f"### Data Profile\n\n**Shape:** {df.shape[0]:,} rows, {df.shape[1]} columns\n")
            mem_usage = df.memory_usage(deep=True).sum() / (1024**2); profile_buffer.write(f"**Memory Usage:** {mem_usage:.2f} MB\n\n")
            profile_buffer.write("**Columns & Non-Null Counts:**\n```\n"); df.info(buf=profile_buffer, verbose=True, show_counts=True); profile_buffer.write("```\n")
            numeric_desc = df.describe(include=np.number)
            if not numeric_desc.empty: profile_buffer.write("\n**Numeric Columns Summary:**\n```\n" + numeric_desc.to_string(float_format="{:,.2f}".format) + "\n```\n")
            object_desc = df.describe(include=['object', 'category'])
            if not object_desc.empty: profile_buffer.write("\n**Categorical Columns Summary:**\n```\n" + object_desc.to_string() + "\n```\n")
            profile_md = profile_buffer.getvalue(); print("Profile generated.")
        except Exception as e: profile_md = f"⚠️ **Profile Generation Error:**\nCould not generate detailed profile.\n```\n{e}\n```"; print(f"Profile generation error: {e}"); traceback.print_exc()
        try: # Null Plot
            null_counts = df.isnull().sum(); null_counts_plot = null_counts[null_counts > 0]
            if not null_counts_plot.empty:
                fig_height_null = max(4, len(null_counts_plot) * 0.3 + 1); fig_null, ax = plt.subplots(figsize=(6, fig_height_null))
                null_counts_plot.sort_values().plot(kind='barh', ax=ax, color='#ffc107', alpha=0.8)
                ax.set_title("Columns with Missing Values", fontsize=10); ax.set_xlabel("Number of Missing Rows", fontsize=9); ax.tick_params(axis='both', which='major', labelsize=8)
                ax.grid(axis='x', linestyle='--', alpha=0.6)
                for index, value in enumerate(null_counts_plot.sort_values()): ax.text(value, index, f' {value:,}', va='center', fontsize=8)
                plt.tight_layout(); null_plot_object = fig_null; plt.close(fig_null); print("Null plot generated.")
            else: print("No missing values found, creating 'No Missing Values' plot."); null_plot_object = create_dummy_plot("No Missing Values Found")
        except Exception as e: null_plot_object = create_dummy_plot("Null Plot Error"); print(f"Null plot error: {e}"); traceback.print_exc()
        try: # Basic Plots
            print("Generating initial basic plots...")
            num_p, cat_p, plot_msgs = generate_basic_plots(df, "Initial"); initial_num_plot = num_p; initial_cat_plot = cat_p
            print("Initial plot generation messages:", plot_msgs)
            current_status_message = final_status_update.get('value', 'Status:') if isinstance(final_status_update, dict) else str(final_status_update)
            if plot_msgs: current_status_message += f"\nInitial Plot Analysis: {'; '.join(plot_msgs)}"
            final_status_update = gr.update(value=current_status_message, visible=True)
        except Exception as basic_plot_e:
             print(f"!!! Error during initial basic plot generation call: {basic_plot_e}"); traceback.print_exc()
             error_status_message = final_status_update.get('value', 'Status:') if isinstance(final_status_update, dict) else str(final_status_update)
             error_status_message += "\n⚠️ Error generating initial plots."
             final_status_update = gr.update(value=error_status_message, visible=True)
             initial_num_plot = create_dummy_plot("Initial Plot Gen Error"); initial_cat_plot = create_dummy_plot("Initial Plot Gen Error")
    else: # No data loaded
        print("No data loaded or file was empty/invalid.")
        profile_md = ""; null_plot_object = null_plot_update_ph.get('value') if isinstance(null_plot_update_ph, dict) else create_dummy_plot("No Data Loaded")
        initial_num_plot = create_dummy_plot("No Data Loaded"); initial_cat_plot = create_dummy_plot("No Data Loaded")
    profile_update = gr.update(value=profile_md, visible=bool(profile_md))
    null_plot_update = gr.update(value=null_plot_object, visible=(null_plot_object is not None))
    initial_num_plot_update = gr.update(value=initial_num_plot, visible=(initial_num_plot is not None))
    initial_cat_plot_update = gr.update(value=initial_cat_plot, visible=(initial_cat_plot is not None))
    # Return 18 updates matching upload_outputs list
    return (
        df, gr.Textbox(visible=False), pv_update, dd_update, profile_update, null_plot_update, date_col_update,
        reset_defaults[11], final_status_update, reset_defaults[12], reset_defaults[13], reset_defaults[6],
        reset_defaults[7], reset_defaults[8], reset_defaults[9], reset_defaults[12], initial_num_plot_update, initial_cat_plot_update
    )

# --- process_and_filter_data function ---
def process_and_filter_data(
    original_df, selected_columns, null_threshold, missing_value_strategy,
    remove_duplicates_flag, trim_whitespace_flag, date_columns_to_standardize,
    apply_special_chars, remove_invalid_phones, add_email_check_col,
    remove_missing_comp_pers, remove_phone_dupes, case_conversion_option, chars_to_remove
    ):
    """ Validates, filters, cleans, reports, captures dupes, generates plots. """
    print("\n--- process_and_filter_data triggered ---")
    processing_steps_log = []
    quality_summary = {}
    initial_cols = original_df.columns.tolist() if original_df is not None else []
    removed_general_duplicates_df = pd.DataFrame(columns=initial_cols)
    removed_phone_duplicates_df = pd.DataFrame(columns=initial_cols)
    cleaned_num_plot = None; cleaned_cat_plot = None; cleaned_df = None; actual_selected_columns = []

    # --- 0. Basic Validation ---
    if original_df is None or original_df.empty:
        error_message = "❌ Error: No data loaded to process. Please upload a file first (Tab 1)."
        print(error_message); return (gr.update(value=None, visible=False), gr.update(value=error_message, visible=True), None, gr.update(visible=False), gr.update(visible=False), gr.update(value="", visible=False), gr.update(value=removed_general_duplicates_df, visible=False), gr.update(value=removed_phone_duplicates_df, visible=False), gr.update(value=create_dummy_plot("Processing Error\nNo Input Data"), visible=True), gr.update(value=create_dummy_plot("Processing Error\nNo Input Data"), visible=True))
    if not selected_columns:
        error_message = "❌ Error: No columns selected to keep. Please select columns in Tab 2."
        print(error_message); return (gr.update(value=None, visible=False), gr.update(value=error_message, visible=True), None, gr.update(visible=False), gr.update(visible=False), gr.update(value="", visible=False), gr.update(value=removed_general_duplicates_df, visible=False), gr.update(value=removed_phone_duplicates_df, visible=False), gr.update(value=create_dummy_plot("Processing Error\nNo Columns Selected"), visible=True), gr.update(value=create_dummy_plot("Processing Error\nNo Columns Selected"), visible=True))

    processing_steps_log.append("📊 **Data Cleaning & Processing Log** 📊"); processing_steps_log.append(f"Start Time: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
    quality_summary["initial_rows"] = len(original_df); quality_summary["initial_cols"] = len(original_df.columns)
    processing_steps_log.append(f"\n**Initial State:** {quality_summary['initial_rows']:,} rows, {quality_summary['initial_cols']} columns.")

    try:
        # --- 1. Column Selection ---
        processing_steps_log.append(f"\n**1. Column Selection:**"); actual_selected_columns = [col for col in selected_columns if col in original_df.columns]; missing_cols = [col for col in selected_columns if col not in actual_selected_columns]
        if not actual_selected_columns: raise ValueError("Error: None of the selected columns exist in the uploaded data. Please re-select columns.")
        if missing_cols: processing_steps_log.append(f"  - Warning: Selected columns not found and ignored: {', '.join(missing_cols)}")
        cleaned_df = original_df[actual_selected_columns].copy(); processing_steps_log.append(f"  - Kept {len(actual_selected_columns)} columns: {', '.join(actual_selected_columns)}"); processing_steps_log.append(f"  - Data shape after selection: {cleaned_df.shape}")

        # --- 2. Handle Missing Values ---
        processing_steps_log.append(f"\n**2. Missing Value Handling:**"); initial_nulls = cleaned_df.isnull().sum().sum(); processing_steps_log.append(f"  - Initial missing values in selected columns: {initial_nulls:,}")
        if missing_value_strategy == "Remove rows with > threshold nulls":
            if null_threshold < len(cleaned_df.columns): max_allowed_nulls = int(null_threshold); initial_rows_mv = len(cleaned_df); required_non_null = len(cleaned_df.columns) - max_allowed_nulls; cleaned_df.dropna(thresh=required_non_null, inplace=True); rows_removed = initial_rows_mv - len(cleaned_df); quality_summary["rows_removed_null_threshold"] = rows_removed; processing_steps_log.append(f"  - Strategy: Remove rows with > {max_allowed_nulls} missing values (keeping rows with >= {required_non_null} non-nulls)."); processing_steps_log.append(f"  - Rows removed: {rows_removed:,}")
            else: processing_steps_log.append(f"  - Strategy: Remove rows with > threshold nulls (Threshold {null_threshold} >= {len(cleaned_df.columns)} cols. No rows removed)."); quality_summary["rows_removed_null_threshold"] = 0
        elif missing_value_strategy == "Fill ALL nulls with Mode":
            processing_steps_log.append(f"  - Strategy: Fill ALL nulls with Mode."); nulls_before_fill = cleaned_df.isnull().sum(); cols_filled = []
            for col in cleaned_df.columns:
                if nulls_before_fill[col] > 0:
                    try: mode_val = cleaned_df[col].mode().dropna();
                    if not mode_val.empty: fill_value = mode_val[0]; cleaned_df[col].fillna(fill_value, inplace=True); cols_filled.append(f"'{col}' (with '{fill_value}')")
                    else: processing_steps_log.append(f"    - Warning: Could not find non-NA mode for '{col}'. Nulls remain.")
                    except Exception as fill_e: processing_steps_log.append(f"    - Error filling '{col}': {fill_e}. Nulls may remain.")
            if cols_filled: processing_steps_log.append(f"  - Filled nulls in columns: {', '.join(cols_filled)}.")
            else: processing_steps_log.append(f"  - No columns required filling or modes could not be determined.")
            final_nulls = cleaned_df.isnull().sum().sum(); processing_steps_log.append(f"  - Total nulls remaining after fill attempt: {final_nulls:,}")
        else: processing_steps_log.append(f"  - Strategy: No missing value handling applied.")
        processing_steps_log.append(f"  - Data shape after MV handling: {cleaned_df.shape}")

        # --- 3. Remove General Duplicates ---
        if remove_duplicates_flag:
            processing_steps_log.append(f"\n**3. Remove General Duplicates:**"); initial_rows_dup = len(cleaned_df); duplicate_mask = cleaned_df.duplicated(keep=False)
            if duplicate_mask.any(): removed_general_duplicates_df = cleaned_df[cleaned_df.duplicated(keep='first')].copy(); cleaned_df.drop_duplicates(keep='first', inplace=True)
            rows_removed = initial_rows_dup - len(cleaned_df); quality_summary["rows_removed_general_duplicates"] = rows_removed; processing_steps_log.append(f"  - Checked for identical rows (kept first occurrence)."); processing_steps_log.append(f"  - Duplicate rows removed: {rows_removed:,}"); processing_steps_log.append(f"  - Data shape after duplicate removal: {cleaned_df.shape}")
        else: processing_steps_log.append(f"\n**3. Remove General Duplicates:** Skipped."); quality_summary["rows_removed_general_duplicates"] = 0

        # --- 4. Trim Whitespace ---
        if trim_whitespace_flag:
            processing_steps_log.append(f"\n**4. Trim Whitespace:**"); trimmed_cols_count = 0; string_cols = cleaned_df.select_dtypes(include=['object']).columns
            if not string_cols.empty:
                for col in string_cols:
                    try:
                        if (cleaned_df[col].astype(str).str.strip() != cleaned_df[col].astype(str)).any(): cleaned_df[col] = cleaned_df[col].astype(str).str.strip(); trimmed_cols_count += 1
                    except Exception as strip_e: processing_steps_log.append(f"    - Warning: Error trimming '{col}': {strip_e}")
                if trimmed_cols_count > 0: processing_steps_log.append(f"  - Trimmed leading/trailing whitespace from {trimmed_cols_count} string column(s).")
                else: processing_steps_log.append(f"  - No leading/trailing whitespace found needing trimming in string columns.")
            else: processing_steps_log.append(f"  - No string columns found to trim.")
        else: processing_steps_log.append(f"\n**4. Trim Whitespace:** Skipped.")

        # --- 5. Case Conversion ---
        if case_conversion_option != "None":
            processing_steps_log.append(f"\n**5. Case Conversion ({case_conversion_option}):**"); converted_cols_count = 0; string_cols = cleaned_df.select_dtypes(include=['object', 'category']).columns
            if not string_cols.empty:
                for col in string_cols:
                    original_dtype = cleaned_df[col].dtype
                    try: col_str = cleaned_df[col].astype(str)
                    if case_conversion_option == "Lowercase":   changed_col = col_str.str.lower()
                    elif case_conversion_option == "Uppercase": changed_col = col_str.str.upper()
                    elif case_conversion_option == "Title Case":changed_col = col_str.str.title()
                    else: changed_col = cleaned_df[col]
                    if not cleaned_df[col].equals(changed_col):
                        cleaned_df[col] = changed_col; converted_cols_count += 1
                        if isinstance(original_dtype, pd.CategoricalDtype): # Use isinstance
                            try: cleaned_df[col] = cleaned_df[col].astype('category')
                            except Exception: pass
                    except Exception as case_e: processing_steps_log.append(f"    - Warning: Error applying case conversion to '{col}': {case_e}")
                if converted_cols_count > 0: processing_steps_log.append(f"  - Applied '{case_conversion_option}' conversion to {converted_cols_count} string/category column(s).")
                else: processing_steps_log.append(f"  - No string/category columns required case conversion.")
            else: processing_steps_log.append(f"  - No string/category columns found to convert.")
        else: processing_steps_log.append(f"\n**5. Case Conversion:** Skipped.")

        # --- 6. Remove Specific Characters ---
        if chars_to_remove:
             processing_steps_log.append(f"\n**6. Remove Specific Characters:**")
             try: escaped_chars = re.escape(chars_to_remove); regex_pattern = f"[{escaped_chars}]"; processing_steps_log.append(f"  - Removing characters: '{chars_to_remove}' (using regex: {regex_pattern})"); removed_in_cols_count = 0; string_cols = cleaned_df.select_dtypes(include=['object', 'category']).columns
             if not string_cols.empty:
                 for col in string_cols:
                      original_dtype = cleaned_df[col].dtype
                      try:
                          if cleaned_df[col].astype(str).str.contains(regex_pattern, regex=True, na=False).any():
                              col_str = cleaned_df[col].astype(str); cleaned_df[col] = col_str.str.replace(regex_pattern, '', regex=True); removed_in_cols_count += 1
                              if isinstance(original_dtype, pd.CategoricalDtype): # Use isinstance
                                   try: cleaned_df[col] = cleaned_df[col].astype('category')
                                   except Exception: pass
                      except Exception as remove_e: processing_steps_log.append(f"    - Warning: Error removing characters from '{col}': {remove_e}")
                 if removed_in_cols_count > 0: processing_steps_log.append(f"  - Removed specified characters from {removed_in_cols_count} string/category column(s).")
                 else: processing_steps_log.append(f"  - Specified characters not found in string/category columns.")
             else: processing_steps_log.append(f"  - No string/category columns found to remove characters from.")
             except re.error as re_err: processing_steps_log.append(f"  - Error: Invalid characters/regex provided for removal: {re_err}. Skipping step.")
             except Exception as e: processing_steps_log.append(f"  - Error during specific character removal: {e}. Skipping step.")
        else: processing_steps_log.append(f"\n**6. Remove Specific Characters:** Skipped (no characters specified).")

        # --- 7. Apply Special Character Rules ---
        if apply_special_chars:
            processing_steps_log.append(f"\n**7. Apply Standardized Character Rules (Regex):**"); cleaned_cols_special_count = 0; rule_applied_to_cols = {}
            for rule in DEFAULT_CLEANING_RULES:
                keywords = rule["keywords"]; regex = rule["remove_chars_regex"]; comment = rule["comment"]
                target_cols = [col for col in cleaned_df.select_dtypes(include=['object', 'category']).columns if any(keyword.lower() in str(col).lower() for keyword in keywords)]
                if target_cols:
                    rule_applied_to_cols[comment] = []
                    for col in target_cols:
                        original_dtype = cleaned_df[col].dtype
                        try:
                            if cleaned_df[col].astype(str).str.contains(regex, regex=True, na=False).any():
                                col_str = cleaned_df[col].astype(str); cleaned_df[col] = col_str.str.replace(regex, '', regex=True)
                                rule_applied_to_cols[comment].append(col); cleaned_cols_special_count += 1
                                if isinstance(original_dtype, pd.CategoricalDtype): # Use isinstance
                                    try: cleaned_df[col] = cleaned_df[col].astype('category')
                                    except Exception: pass
                        except Exception as special_e: processing_steps_log.append(f"    - Warning: Error applying rule '{comment}' to '{col}': {special_e}")
                    if rule_applied_to_cols[comment]: processing_steps_log.append(f"  - Rule '{comment}' (Regex: {regex}) applied to clean: {', '.join(sorted(list(set(rule_applied_to_cols[comment]))))}")
            if cleaned_cols_special_count == 0: processing_steps_log.append(f"  - No columns required modification based on the standardized rules.")
        else: processing_steps_log.append(f"\n**7. Apply Standardized Character Rules:** Skipped.")

        # --- Find relevant columns ---
        current_string_cols = cleaned_df.select_dtypes(include=['object', 'category']).columns
        phone_cols = [col for col in current_string_cols if any(k in str(col).lower() for k in ["phone", "mobile", "contact"])]; email_cols = [col for col in current_string_cols if "email" in str(col).lower()]
        company_cols = [col for col in cleaned_df.columns if any(k in str(col).lower() for k in ["company", "organization", "account", "firm"])]
        person_cols = [col for col in cleaned_df.columns if any(k in str(col).lower() for k in ["name", "person", "contact name", "full name", "contact_person"])]

        # --- 8. Remove Invalid Phone Rows ---
        if remove_invalid_phones and phone_cols:
            processing_steps_log.append(f"\n**8. Remove Invalid Phone Rows:**"); initial_rows_phone_val = len(cleaned_df); rows_to_drop_indices = pd.Index([]); phone_validation_regex = r'^[6-9]\d{9}$'
            processing_steps_log.append(f"  - Validating phone format (Regex: {phone_validation_regex}) in columns: {', '.join(phone_cols)}")
            for col in phone_cols:
                try: digits_only = cleaned_df[col].astype(str).str.replace(r'\D', '', regex=True); invalid_mask = (~digits_only.str.match(phone_validation_regex, na=True)) & cleaned_df[col].notna() & (cleaned_df[col] != ''); rows_to_drop_indices = rows_to_drop_indices.union(cleaned_df[invalid_mask].index)
                except Exception as phone_val_e: processing_steps_log.append(f"    - Warning: Error processing phone column '{col}' for validation: {phone_val_e}")
            if not rows_to_drop_indices.empty: cleaned_df.drop(rows_to_drop_indices, inplace=True)
            rows_removed = initial_rows_phone_val - len(cleaned_df); quality_summary["rows_removed_invalid_phone"] = rows_removed; processing_steps_log.append(f"  - Rows removed due to invalid phone format: {rows_removed:,}"); processing_steps_log.append(f"  - Data shape after phone validation: {cleaned_df.shape}")
        elif remove_invalid_phones: processing_steps_log.append(f"\n**8. Remove Invalid Phone Rows:** Skipped (no columns identified containing 'phone', 'mobile', or 'contact').")
        else: processing_steps_log.append(f"\n**8. Remove Invalid Phone Rows:** Skipped."); quality_summary["rows_removed_invalid_phone"] = 0

        # --- 9. Remove Phone Duplicates ---
        if remove_phone_dupes and phone_cols:
            processing_steps_log.append(f"\n**9. Remove Phone Duplicates:**"); initial_rows_phone_dup = len(cleaned_df); dedupe_phone_col = phone_cols[0]; processing_steps_log.append(f"  - Checking duplicates based ONLY on digits in column: '{dedupe_phone_col}' (keeps first occurrence).")
            try: cleaned_digits = cleaned_df[dedupe_phone_col].astype(str).str.replace(r'\D', '', regex=True); cleaned_digits = cleaned_digits.replace('', pd.NA); duplicate_indices = cleaned_df[cleaned_digits.duplicated(keep='first') & cleaned_digits.notna()].index
            if not duplicate_indices.empty: removed_phone_duplicates_df = cleaned_df.loc[duplicate_indices].copy(); cleaned_df.drop(duplicate_indices, inplace=True)
            rows_removed = initial_rows_phone_dup - len(cleaned_df); quality_summary["rows_removed_phone_duplicates"] = rows_removed; processing_steps_log.append(f"  - Duplicate phone rows removed: {rows_removed:,}"); processing_steps_log.append(f"  - Data shape after phone duplicate removal: {cleaned_df.shape}")
            except Exception as phone_dedup_e: processing_steps_log.append(f"    - Warning: Error during phone deduplication on column '{dedupe_phone_col}': {phone_dedup_e}"); quality_summary["rows_removed_phone_duplicates"] = 0
        elif remove_phone_dupes: processing_steps_log.append(f"\n**9. Remove Phone Duplicates:** Skipped (no columns identified containing 'phone', 'mobile', or 'contact').")
        else: processing_steps_log.append(f"\n**9. Remove Phone Duplicates:** Skipped."); quality_summary["rows_removed_phone_duplicates"] = 0

        # --- 10. Add Email Validity Column ---
        if add_email_check_col and email_cols:
             processing_steps_log.append(f"\n**10. Add Email Validity Column:**"); email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"; target_email_col = email_cols[0]; base_validity_col_name = f"{target_email_col}_Validity"; validity_col_name = base_validity_col_name; counter = 1
             while validity_col_name in cleaned_df.columns: validity_col_name = f"{base_validity_col_name}_{counter}"; counter += 1
             processing_steps_log.append(f"  - Checking format in column: '{target_email_col}' using Regex."); processing_steps_log.append(f"  - Adding column: '{validity_col_name}'")
             try: email_series = cleaned_df[target_email_col].astype(str); is_valid = email_series.str.match(email_regex, na=False); cleaned_df[validity_col_name] = np.select([ is_valid, email_series.isin(['', 'nan', 'None', '<NA>']) | cleaned_df[target_email_col].isna() ], [ 'Valid Format', 'Missing' ], default='Invalid Format'); cleaned_df[validity_col_name] = cleaned_df[validity_col_name].astype('category')
             valid_count = (cleaned_df[validity_col_name] == 'Valid Format').sum(); invalid_count = (cleaned_df[validity_col_name] == 'Invalid Format').sum(); missing_count = (cleaned_df[validity_col_name] == 'Missing').sum(); processing_steps_log.append(f"  - Results: {valid_count:,} Valid Format, {invalid_count:,} Invalid Format, {missing_count:,} Missing.")
             if validity_col_name not in actual_selected_columns: actual_selected_columns.append(validity_col_name)
             except Exception as email_check_e: processing_steps_log.append(f"    - Error adding email validity column: {email_check_e}");
             if validity_col_name in cleaned_df.columns: cleaned_df.drop(columns=[validity_col_name], inplace=True)
        elif add_email_check_col: processing_steps_log.append(f"\n**10. Add Email Validity Column:** Skipped (no columns identified containing 'email').")
        else: processing_steps_log.append(f"\n**10. Add Email Validity Column:** Skipped.")

        # --- 11. Remove Row if Missing Company & Person ---
        if remove_missing_comp_pers:
            processing_steps_log.append(f"\n**11. Remove Row if Missing Company & Person:**"); initial_rows_comp_pers = len(cleaned_df)
            if company_cols and person_cols:
                processing_steps_log.append(f"  - Checking for missing values in Company cols ({', '.join(company_cols)}) AND Person cols ({', '.join(person_cols)})")
                try: missing_company_mask = cleaned_df[company_cols].isna().all(axis=1) | (cleaned_df[company_cols].astype(str) == '').all(axis=1); missing_person_mask = cleaned_df[person_cols].isna().all(axis=1) | (cleaned_df[person_cols].astype(str) == '').all(axis=1); combined_missing_mask = missing_company_mask & missing_person_mask; rows_to_drop_cp_indices = cleaned_df[combined_missing_mask].index
                if not rows_to_drop_cp_indices.empty: cleaned_df.drop(rows_to_drop_cp_indices, inplace=True)
                rows_removed = initial_rows_comp_pers - len(cleaned_df); quality_summary["rows_removed_missing_comp_pers"] = rows_removed; processing_steps_log.append(f"  - Rows removed where Company AND Person fields were both empty/missing: {rows_removed:,}"); processing_steps_log.append(f"  - Data shape after Comp/Pers check: {cleaned_df.shape}")
                except Exception as cp_check_e: processing_steps_log.append(f"    - Error during Company/Person check: {cp_check_e}"); quality_summary["rows_removed_missing_comp_pers"] = 0
            else: missing_keywords = [];
            if not company_cols: missing_keywords.append("Company/Organization/Account")
            if not person_cols: missing_keywords.append("Name/Person/Contact Name")
            processing_steps_log.append(f"  - Skipped: Could not identify columns for: {', '.join(missing_keywords)} based on keywords."); quality_summary["rows_removed_missing_comp_pers"] = 0
        else: processing_steps_log.append(f"\n**11. Remove Row if Missing Company & Person:** Skipped."); quality_summary["rows_removed_missing_comp_pers"] = 0

        # --- 12. Date Standardization ---
        if date_columns_to_standardize:
            processing_steps_log.append(f"\n**12. Date Standardization:**"); standardized_cols_date_count = 0; not_found_date_cols = []; error_date_cols = []
            for col in date_columns_to_standardize:
                if col in cleaned_df.columns:
                    if pd.api.types.is_datetime64_any_dtype(cleaned_df[col]): # is_datetime64_any_dtype is okay
                        processing_steps_log.append(f"  - Column '{col}' is already datetime type. Formatting to YYYY-MM-DD.")
                        try: cleaned_df[col] = cleaned_df[col].dt.strftime('%Y-%m-%d'); standardized_cols_date_count += 1
                        except Exception as date_format_e: processing_steps_log.append(f"    - Error formatting already-datetime column '{col}': {date_format_e}."); error_date_cols.append(col)
                        continue
                    processing_steps_log.append(f"  - Attempting to parse and standardize '{col}' to YYYY-MM-DD format.")
                    try: original_null_mask = cleaned_df[col].isna() | (cleaned_df[col] == ''); parsed_dates = pd.to_datetime(cleaned_df[col], errors='coerce'); cleaned_df[col] = parsed_dates.dt.strftime('%Y-%m-%d'); failed_parses_mask = parsed_dates.isna() & ~original_null_mask; failed_parses_count = failed_parses_mask.sum()
                    if failed_parses_count > 0: processing_steps_log.append(f"    - Note: {failed_parses_count:,} values in '{col}' could not be parsed and were set to null.")
                    standardized_cols_date_count += 1
                    except Exception as date_e: processing_steps_log.append(f"    - Error parsing or formatting '{col}': {date_e}. Column left unchanged."); error_date_cols.append(col)
                else: not_found_date_cols.append(col)
            if standardized_cols_date_count > 0: processing_steps_log.append(f"  - Successfully standardized {standardized_cols_date_count} date column(s).")
            if not_found_date_cols: processing_steps_log.append(f"  - Warning: Selected date columns not found: {', '.join(not_found_date_cols)}.")
            if error_date_cols: processing_steps_log.append(f"  - Warning: Errors occurred while processing date columns: {', '.join(list(set(error_date_cols)))}.")
            if not date_columns_to_standardize: processing_steps_log.append(f"  - No date columns were selected for standardization.")
        else: processing_steps_log.append(f"\n**12. Date Standardization:** Skipped (no columns selected).")

        # --- 13. Generate Plots ---
        processing_steps_log.append(f"\n**13. Generate Visualizations for Cleaned Data:**"); print("Generating plots for cleaned data...")
        if cleaned_df is not None and not cleaned_df.empty:
            try: num_p, cat_p, plot_msgs = generate_basic_plots(cleaned_df, "Cleaned"); cleaned_num_plot = num_p; cleaned_cat_plot = cat_p; print("Cleaned plot generation messages:", plot_msgs)
            if plot_msgs: processing_steps_log.append(f"  - Generated plots: {', '.join(plot_msgs)}.")
            else: processing_steps_log.append("  - No suitable data found for standard plots.")
            except Exception as cleaned_plot_e: print(f"!!! Error during cleaned plot generation call: {cleaned_plot_e}"); traceback.print_exc(); processing_steps_log.append(f"  - ⚠️ Warning: Failed to generate plots for cleaned data."); cleaned_num_plot = create_dummy_plot("Cleaned Plot Gen Error"); cleaned_cat_plot = create_dummy_plot("Cleaned Plot Gen Error")
        else: processing_steps_log.append("  - Info: No cleaned data available to generate plots."); print("[Process] No cleaned data, creating dummy plots."); cleaned_num_plot = create_dummy_plot("No Cleaned Data"); cleaned_cat_plot = create_dummy_plot("No Cleaned Data")

        # --- 14. Final Summary ---
        processing_steps_log.append(f"\n**14. Final Summary:**"); final_rows = len(cleaned_df) if cleaned_df is not None else 0; final_cols = len(cleaned_df.columns) if cleaned_df is not None else 0
        quality_summary["final_rows"] = final_rows; quality_summary["final_cols"] = final_cols; total_rows_removed = quality_summary.get("initial_rows", 0) - final_rows
        processing_steps_log.append(f"  - Processing completed at: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
        processing_steps_log.append(f"  - **Final Data Shape:** {final_rows:,} rows, {final_cols} columns."); processing_steps_log.append(f"  - **Total Rows Removed:** {total_rows_removed:,}")
        removals_log = [];
        if quality_summary.get("rows_removed_null_threshold", 0) > 0: removals_log.append(f"Missing Value Threshold ({quality_summary['rows_removed_null_threshold']:,})")
        if quality_summary.get("rows_removed_general_duplicates", 0) > 0: removals_log.append(f"General Duplicates ({quality_summary['rows_removed_general_duplicates']:,})")
        if quality_summary.get("rows_removed_invalid_phone", 0) > 0: removals_log.append(f"Invalid Phone Format ({quality_summary['rows_removed_invalid_phone']:,})")
        if quality_summary.get("rows_removed_phone_duplicates", 0) > 0: removals_log.append(f"Duplicate Phone Numbers ({quality_summary['rows_removed_phone_duplicates']:,})")
        if quality_summary.get("rows_removed_missing_comp_pers", 0) > 0: removals_log.append(f"Missing Company & Person ({quality_summary['rows_removed_missing_comp_pers']:,})")
        if removals_log: processing_steps_log.append(f"    - Removals Breakdown: {'; '.join(removals_log)}")

        # --- 15. Generate Download Links ---
        link_html = ""; show_outputs = cleaned_df is not None and not cleaned_df.empty
        if show_outputs:
             print("Generating download links..."); link_parts = []
             try: csv_buffer_clean = io.StringIO(); cleaned_df.to_csv(csv_buffer_clean, index=False, encoding='utf-8'); csv_buffer_clean.seek(0); csv_b64_clean = base64.b64encode(csv_buffer_clean.getvalue().encode('utf-8')).decode('utf-8'); dl_filename_clean = "cleaned_data.csv"; link_parts.append(f'<a href="data:text/csv;base64,{csv_b64_clean}" download="{dl_filename_clean}" class="gr-button gr-button-primary" style="background: #28a745 !important; border-color: #28a745 !important;">💾 Download Cleaned Data (CSV)</a>')
             if remove_duplicates_flag and not removed_general_duplicates_df.empty: csv_buffer_dups = io.StringIO(); removed_general_duplicates_df.to_csv(csv_buffer_dups, index=False, encoding='utf-8'); csv_buffer_dups.seek(0); csv_b64_dups = base64.b64encode(csv_buffer_dups.getvalue().encode('utf-8')).decode('utf-8'); dl_filename_dups = "removed_general_duplicates.csv"; link_parts.append(f'<a href="data:text/csv;base64,{csv_b64_dups}" download="{dl_filename_dups}" class="gr-button" style="background: #ffc107 !important; border-color: #ffc107 !important; color: #343a40 !important;">📋 Download General Duplicates (CSV)</a>')
             if remove_phone_dupes and not removed_phone_duplicates_df.empty: csv_buffer_phone_dups = io.StringIO(); removed_phone_duplicates_df.to_csv(csv_buffer_phone_dups, index=False, encoding='utf-8'); csv_buffer_phone_dups.seek(0); csv_b64_phone_dups = base64.b64encode(csv_buffer_phone_dups.getvalue().encode('utf-8')).decode('utf-8'); dl_filename_phone_dups = "removed_phone_duplicates.csv"; link_parts.append(f'<a href="data:text/csv;base64,{csv_b64_phone_dups}" download="{dl_filename_phone_dups}" class="gr-button" style="background: #ffc107 !important; border-color: #ffc107 !important; color: #343a40 !important;">📱 Download Phone Duplicates (CSV)</a>')
             link_html = "\n".join(link_parts)
             except Exception as link_e: print(f"Error generating download links: {link_e}"); traceback.print_exc(); processing_steps_log.append(f"\n⚠️ Error generating download links: {link_e}"); link_html = "<p style='color:red;'>Error generating one or more download links.</p>"
        else: processing_steps_log.append(f"\n**15. Download Links:** Skipped (No cleaned data to download).")

        status_message = "\n".join(processing_steps_log)
        if removed_general_duplicates_df.empty: removed_general_duplicates_df = pd.DataFrame(columns=initial_cols)
        if removed_phone_duplicates_df.empty: removed_phone_duplicates_df = pd.DataFrame(columns=initial_cols)

        print("Processing finished successfully.")
        # --- Return 10 items ---
        return (gr.update(value=cleaned_df, visible=show_outputs), gr.update(value=status_message, visible=True), cleaned_df, gr.update(visible=False), gr.update(visible=False), gr.update(value=link_html, visible=show_outputs and bool(link_html)), gr.update(value=removed_general_duplicates_df, visible=not removed_general_duplicates_df.empty), gr.update(value=removed_phone_duplicates_df, visible=not removed_phone_duplicates_df.empty), gr.update(value=cleaned_num_plot, visible=(cleaned_num_plot is not None)), gr.update(value=cleaned_cat_plot, visible=(cleaned_cat_plot is not None)))

    # --- Exception Handling ---
    except Exception as e:
        print(f"!!! FATAL ERROR in process_and_filter_data: {e}"); traceback.print_exc(); error_log = processing_steps_log + ["\n---", f"❌ **FATAL PROCESSING ERROR:**", traceback.format_exc()]; error_message = "\n".join(error_log)
        error_num_plot = create_dummy_plot("Processing Error"); error_cat_plot = create_dummy_plot("Processing Error")
        empty_df_cols = actual_selected_columns if 'actual_selected_columns' in locals() else initial_cols; empty_df = pd.DataFrame(columns=empty_df_cols)
        return (gr.update(value=None, visible=False), gr.update(value=error_message, visible=True), None, gr.update(visible=False), gr.update(visible=False), gr.update(value="", visible=False), gr.update(value=empty_df, visible=False), gr.update(value=empty_df, visible=False), gr.update(value=error_num_plot, visible=True), gr.update(value=error_cat_plot, visible=True))

# --- reset_all function ---
def reset_all():
    """ Resets all UI components to their initial state. Returns 27 updates. """
    print("Resetting application state...")
    reset_num_plot = create_dummy_plot("Upload Data to View Plot"); reset_cat_plot = create_dummy_plot("Upload Data to View Plot"); reset_null_plot = create_dummy_plot("Upload Data to View Plot")
    initial_status = "Status: Ready. Please upload a file to begin."
    # Return 27 updates matching reset_outputs list in build_ui
    return ( gr.update(value=None), gr.update(value=None, visible=False), gr.update(choices=[], value=[], interactive=False), gr.update(value="", visible=False), gr.update(value=reset_null_plot, visible=True), gr.update(choices=[], value=[], interactive=False), gr.update(value=2, visible=True, interactive=True), gr.update(value="Remove rows with > threshold nulls"), gr.update(value=True), gr.update(value=True), gr.update(value=initial_status, visible=True), gr.update(value=None, visible=False), gr.update(visible=False), gr.update(value="", visible=False), None, None, gr.update(value=None, visible=False), gr.update(value=None, visible=False), gr.update(value=reset_num_plot, visible=True), gr.update(value=reset_cat_plot, visible=True), gr.update(value=True), gr.update(value=True), gr.update(value=True), gr.update(value=False), gr.update(value=True), gr.update(value="None"), gr.update(value="") )

# --- update_slider_visibility function ---
def update_slider_visibility(choice):
    """Controls visibility of the null threshold slider."""
    is_visible = (choice == "Remove rows with > threshold nulls")
    print(f"Missing value strategy changed to: '{choice}'. Slider visible: {is_visible}")
    return gr.update(visible=is_visible, interactive=is_visible)

# --- hide_results function (Helper, used by lambda) ---
def hide_results():
    """ Hides components in the results tab and potentially initial analysis. """
    print("Hiding results details...")
    # Returns 12 updates matching hide_results_outputs lambda in build_ui
    return ( gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False) )

# --- Load CSS ---
def load_css(css_path):
    """Loads CSS from a file."""
    if css_path.is_file():
        print(f"Loading CSS from: {css_path}")
        with open(css_path, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        print(f"Warning: CSS file not found at {css_path}. Using default styles.")
        return ""

# --- Build Gradio UI Function ---
def build_ui():
    """Builds the Gradio interface."""
    print("Building Gradio UI...")
    css_styling = load_css(CSS_FILE_PATH)

    with gr.Blocks(title="Data Cleaner Pro v1.5", css=css_styling, theme=gr.themes.Soft()) as app:

        gr.Markdown("<h1>🧹 Data Cleaner Pro ✨</h1>")
        gr.Markdown("<p style='text-align:center; color: #6c757d; margin-top:-15px; margin-bottom:20px;'>Upload, clean, and visualize your tabular data.</p>")

        # --- State Variables ---
        original_df_state = gr.State(None)
        cleaned_df_state = gr.State(None)

        # --- Define Tabs and Layout ---
        with gr.Tabs() as main_tabs:
            # =================== TAB 1: Upload & Profile ===================
            with gr.TabItem("1. Upload & Initial Analysis", id=0):
                with gr.Row():
                    with gr.Column(scale=2):
                        file_input = gr.File(label="📁 Upload CSV or XLSX File", file_types=['.csv', '.xlsx', '.xls'], elem_classes="gr-file")
                        status_info_box = gr.Textbox(label="ℹ️ Status & Info", value="Status: Ready. Please upload a file.", interactive=False, lines=3, elem_id="status-textbox")
                    with gr.Column(scale=3):
                        with gr.Accordion("🧐 View Raw Data Preview (First 5 Rows)", open=False):
                             data_preview = gr.DataFrame(label="Raw Data Preview", visible=False, interactive=False, row_count=(5, "fixed"), col_count=(10, "dynamic"), wrap=True, elem_classes="gr-dataframe")
                gr.Markdown("---"); gr.Markdown("### Initial Data Insights")
                with gr.Row():
                     with gr.Column(scale=3): profile_display = gr.Markdown(label="Data Profile", visible=False, elem_id="profile-display")
                     with gr.Column(scale=2):
                         with gr.Tabs():
                             with gr.TabItem("Missing Values"): null_plot_display = gr.Plot(label=None, visible=True, elem_id="null-plot-display", show_label=False, value=create_dummy_plot("Upload Data to View Plot")) # Show placeholder
                             with gr.TabItem("Numeric Dist."): initial_numeric_plot = gr.Plot(label=None, visible=True, elem_id="initial-num-plot", show_label=False, value=create_dummy_plot("Upload Data to View Plot")) # Show placeholder
                             with gr.TabItem("Categorical Counts"): initial_categorical_plot = gr.Plot(label=None, visible=True, elem_id="initial-cat-plot", show_label=False, value=create_dummy_plot("Upload Data to View Plot")) # Show placeholder

            # =================== TAB 2: Configure Cleaning ===================
            with gr.TabItem("2. Configure Cleaning Steps", id=1):
                gr.Markdown("### Select Columns & Apply Cleaning Rules")
                with gr.Row():
                    with gr.Column(scale=1): gr.Markdown("#### 1. Select Columns to Keep:"); column_selector = gr.CheckboxGroup(label=None, show_label=False, interactive=False, elem_id="column-selector-checkbox")
                    with gr.Column(scale=2):
                        gr.Markdown("#### 2. Choose Cleaning Options:")
                        with gr.Group(elem_classes="config-group"): # Basic
                            gr.Markdown("##### Basic Operations")
                            with gr.Row(): trim_whitespace_checkbox = gr.Checkbox(label="Trim Whitespace", value=True, info="Remove leading/trailing spaces.", scale=1, elem_classes="checkbox-group"); remove_duplicates_checkbox = gr.Checkbox(label="Remove Duplicate Rows", value=True, info="Remove identical rows (keeps first).", scale=1, elem_classes="checkbox-group")
                            with gr.Row(): case_conversion_radio = gr.Radio(["None", "Lowercase", "Uppercase", "Title Case"], label="Convert Text Case:", value="None", info="Apply to string columns.", scale=1); remove_chars_textbox = gr.Textbox(label="Remove Specific Characters:", placeholder="e.g., #$%*", info="Enter characters to remove literally.", lines=1, scale=1)
                        with gr.Group(elem_classes="config-group"): # Column Specific
                             gr.Markdown("##### Column-Specific Rules");
                             with gr.Row(): apply_special_chars_checkbox = gr.Checkbox(label="Standardize Special Chars", value=True, info="Apply predefined regex rules (e.g., for emails, phones, names).", elem_classes="checkbox-group", scale=1); add_email_check_col_checkbox = gr.Checkbox(label="Add Email Validity Column", value=True, info="Add column checking basic email format.", elem_classes="checkbox-group", scale=1)
                             with gr.Row(): remove_invalid_phones_checkbox = gr.Checkbox(label="Remove Invalid Phones", value=True, info="Remove rows with invalid phone format (India: 10 digits, 6-9 start).", elem_classes="checkbox-group", scale=1); remove_phone_dupes_checkbox = gr.Checkbox(label="Remove Phone Duplicates", value=True, info="Remove rows based ONLY on duplicate phone numbers (keeps first).", elem_classes="checkbox-group", scale=1)
                             with gr.Row(): remove_missing_comp_pers_checkbox = gr.Checkbox(label="Remove if Missing Company & Person", value=False, info="Remove row if common 'Company' AND 'Name/Person' fields are both empty.", elem_classes="checkbox-group")
                        with gr.Group(elem_classes="config-group"): # Dates
                             gr.Markdown("##### Date Handling"); date_cols_selector = gr.CheckboxGroup(label="Select Date Columns to Standardize (to YYYY-MM-DD):", info="Select from kept columns.", interactive=False, elem_id="date-cols-selector")
                        with gr.Group(elem_classes="config-group"): # Missing Values
                             gr.Markdown("##### Missing Value Handling"); missing_value_radio = gr.Radio(["Remove rows with > threshold nulls", "Fill ALL nulls with Mode"], label="Strategy:", value="Remove rows with > threshold nulls", info="Choose how to handle rows with missing data.")
                             null_threshold_slider = gr.Slider(minimum=0, maximum=10, step=1, value=2, label="Null Threshold", info="If using threshold strategy, remove rows with more than this many nulls.", interactive=True, visible=True)
                gr.Markdown("---"); process_btn = gr.Button("🚀 Apply Cleaning & View Results", variant="primary", size='lg')

            # =================== TAB 3: Results ===================
            with gr.TabItem("3. View & Download Results", id=2):
                gr.Markdown("### Processing Results")
                with gr.Row():
                    with gr.Column(scale=2): processing_log_display = gr.Textbox(label="📊 Processing Log & Summary", interactive=False, visible=False, lines=20, elem_id="status-textbox")
                    with gr.Column(scale=1):
                         gr.Markdown("#### Download Center"); download_link_html = gr.HTML(visible=False, elem_id="download-links")
                         gr.Markdown("#### Cleaned Data Visuals")
                         with gr.Tabs():
                              with gr.TabItem("Numeric Dist."): cleaned_numeric_plot = gr.Plot(label=None, show_label=False, visible=False, elem_id="cleaned-num-plot")
                              with gr.TabItem("Categorical Counts"): cleaned_categorical_plot = gr.Plot(label=None, show_label=False, visible=False, elem_id="cleaned-cat-plot")
                gr.Markdown("---"); gr.Markdown("### Cleaned Data Table")
                cleaned_data_display = gr.DataFrame(label=None, show_label=False, visible=False, interactive=False, row_count=(10, "dynamic"), col_count=(10, "dynamic"), wrap=True, elem_classes="gr-dataframe" )
                with gr.Row(): # Removed Rows Accordions
                    with gr.Column():
                         with gr.Accordion("🚮 Show/Hide Removed General Duplicate Rows", open=False, visible=False) as removed_general_accordion:
                             removed_general_duplicates_display = gr.DataFrame(label=None, show_label=False, interactive=False, row_count=(5, "dynamic"), wrap=True, elem_classes="gr-dataframe")
                    with gr.Column():
                         with gr.Accordion("📱 Show/Hide Removed Phone Duplicate Rows", open=False, visible=False) as removed_phone_accordion:
                             removed_phone_duplicates_display = gr.DataFrame(label=None, show_label=False, interactive=False, row_count=(5, "dynamic"), wrap=True, elem_classes="gr-dataframe")
                hide_results_btn = gr.Button(" HIDE RESULTS & LOGS", visible=False, elem_id="hide-results-button", icon="🙈")

        # --- Global Reset Button ---
        reset_btn = gr.Button("🔄 Reset Application State", elem_id="reset-button", size='sm', scale=0)
        gr.Markdown("<hr style='border-color:#dee2e6; margin-top: 30px;'><p id='app-footer'>Data Cleaner Pro v1.5</p>")

        # =================== Define Interactions ===================
        print("Defining Gradio component interactions...")

        # 1. Upload Interaction (Outputs list MUST match handle_file_upload return tuple order)
        upload_outputs = [ original_df_state, gr.Textbox(visible=False), data_preview, column_selector, profile_display, null_plot_display, date_cols_selector, cleaned_data_display, status_info_box, gr.Button(visible=False), gr.Button(visible=False), null_threshold_slider, missing_value_radio, remove_duplicates_checkbox, trim_whitespace_checkbox, hide_results_btn, initial_numeric_plot, initial_categorical_plot ]
        file_input.upload(fn=handle_file_upload, inputs=file_input, outputs=upload_outputs, show_progress="full")

        # 2. Process Trigger (Inputs/Outputs lists MUST match process_and_filter_data signature/return tuple order)
        processing_inputs = [ original_df_state, column_selector, null_threshold_slider, missing_value_radio, remove_duplicates_checkbox, trim_whitespace_checkbox, date_cols_selector, apply_special_chars_checkbox, remove_invalid_phones_checkbox, add_email_check_col_checkbox, remove_missing_comp_pers_checkbox, remove_phone_dupes_checkbox, case_conversion_radio, remove_chars_textbox ]
        processing_outputs = [ cleaned_data_display, processing_log_display, cleaned_df_state, gr.Button(visible=False), gr.Button(visible=False), download_link_html, removed_general_duplicates_display, removed_phone_duplicates_display, cleaned_numeric_plot, cleaned_categorical_plot ]
        process_btn.click(fn=process_and_filter_data, inputs=processing_inputs, outputs=processing_outputs)
        # -- Visibility Update & Tab Switch for Process --
        results_visibility_outputs = [ processing_log_display, cleaned_data_display, hide_results_btn, download_link_html, removed_general_accordion, removed_phone_accordion, cleaned_numeric_plot, cleaned_categorical_plot ]
        process_btn.click( fn=lambda: (gr.update(visible=True), gr.update(visible=True), gr.update(visible=True), gr.update(visible=True), gr.update(visible=True), gr.update(visible=True), gr.update(), gr.update()), inputs=None, outputs=results_visibility_outputs )
        process_btn.click(lambda: gr.Tabs(selected=2), inputs=None, outputs=main_tabs)

        # 3. Conditional Slider Visibility
        missing_value_radio.change(fn=update_slider_visibility, inputs=[missing_value_radio], outputs=[null_threshold_slider])

        # 4. Reset Button Interaction (Outputs list MUST match reset_all return tuple order)
        reset_outputs = [ file_input, data_preview, column_selector, profile_display, null_plot_display, date_cols_selector, null_threshold_slider, missing_value_radio, remove_duplicates_checkbox, trim_whitespace_checkbox, status_info_box, cleaned_data_display, hide_results_btn, download_link_html, original_df_state, cleaned_df_state, removed_general_duplicates_display, removed_phone_duplicates_display, initial_numeric_plot, initial_categorical_plot, apply_special_chars_checkbox, remove_invalid_phones_checkbox, add_email_check_col_checkbox, remove_missing_comp_pers_checkbox, remove_phone_dupes_checkbox, case_conversion_radio, remove_chars_textbox ]
        reset_btn.click(fn=reset_all, inputs=None, outputs=reset_outputs)
        # -- Visibility Update & Tab Switch for Reset --
        reset_visibility_outputs = [ processing_log_display, cleaned_data_display, hide_results_btn, download_link_html, removed_general_accordion, removed_phone_accordion, cleaned_numeric_plot, cleaned_categorical_plot ]
        reset_btn.click(fn=lambda: (gr.update(visible=False),)*8, inputs=None, outputs=reset_visibility_outputs)
        reset_btn.click(lambda: gr.Tabs(selected=0), inputs=None, outputs=main_tabs)

        # 5. Hide Results Button Interaction
        hide_results_outputs = [ cleaned_data_display, processing_log_display, hide_results_btn, download_link_html, removed_general_accordion, removed_phone_accordion, cleaned_numeric_plot, cleaned_categorical_plot, profile_display, null_plot_display, initial_numeric_plot, initial_categorical_plot ]
        hide_results_btn.click(fn=lambda: (gr.update(visible=False),)*12, inputs=None, outputs=hide_results_outputs)

    return app

# --- Main Execution Block ---
if __name__ == "__main__":
    if libraries_ready:
        app_instance = build_ui()
        print("\n--- Launching Gradio App ---")
        print("Interface defined. Launching server...")
        try:
            # Launch the app
            app_instance.launch(debug=False, share=False) # Set share=True if needed for external access
            print("\nGradio app launched. Access it via the local URL provided above.")
            print("Press Ctrl+C in the terminal to stop the server.")
        except Exception as launch_e:
            print(f"\n--- GRADIO LAUNCH ERROR ---")
            print(f"Failed to launch app: {launch_e}")
            traceback.print_exc()
            print("Please check for port conflicts or other issues.")
            print("---------------------------")
    else:
        # Message already printed by check_libraries()
        print("\nApplication cannot start due to missing libraries.")