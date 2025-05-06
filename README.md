# 🧹 Data Cleaner Pro ✨

An interactive web application built with Gradio and Pandas to easily clean and preprocess tabular data (CSV/XLSX files). Upload your data, configure cleaning steps through a user-friendly interface, visualize the results, and download the cleaned dataset.


## 🚀 Features

*   **File Upload:** Supports CSV, XLSX, and XLS file formats.
*   **Data Preview:** View the first few rows of your raw data.
*   **Initial Analysis:** Automatically generates:
    *   Data profile (shape, columns, types, memory usage).
    *   Missing value counts plot.
    *   Basic distribution plots for numeric and categorical features.
*   **Column Selection:** Choose which columns to keep in the final dataset.
*   **Configurable Cleaning Steps:**
    *   **Missing Value Handling:**
        *   Remove rows exceeding a specified null value threshold.
        *   Fill all missing values with the column's mode.
    *   **Duplicate Removal:**
        *   Remove identical rows (general duplicates).
        *   Remove rows based *only* on duplicate phone numbers.
    *   **Text Cleaning:**
        *   Trim leading/trailing whitespace.
        *   Convert text case (lowercase, uppercase, title case).
        *   Remove specific user-defined characters.
        *   Apply standardized cleaning rules (regex-based) for common fields like emails, phones, names.
    *   **Data Validation & Enrichment:**
        *   Remove rows with invalid phone number formats (defaults to Indian format, adjustable in code).
        *   Add a new column indicating basic email format validity.
    *   **Row Filtering:**
        *   Optionally remove rows where both company and person/name fields are missing.
    *   **Date Standardization:**
        *   Convert selected columns to `YYYY-MM-DD` format (attempts various input formats).
*   **Results Visualization:** View distribution plots for the cleaned data.
*   **Processing Log:** See a detailed step-by-step summary of the cleaning actions performed.
*   **Download Results:** Download the cleaned dataset and optionally the rows removed due to duplication (as separate CSV files).

## ⚙️ Requirements

*   Python 3.8+
*   Libraries listed in `requirements.txt`:
    *   pandas
    *   gradio
    *   openpyxl (for Excel support)
    *   matplotlib
    *   numpy

## 🛠️ Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/data-cleaner-pro.git
    cd data-cleaner-pro
    ```
    *(Replace `your-username` with your actual GitHub username)*

2.  **Set up a virtual environment (Recommended):**
    ```bash
    python -m venv venv
    # Activate the environment (Linux/macOS)
    source venv/bin/activate
    # Activate the environment (Windows - Command Prompt/PowerShell)
    # venv\Scripts\activate
    ```

3.  **Install the required libraries:**
    ```bash
    pip install -r requirements.txt
    ```

## ▶️ Usage

1.  **Run the application:**
    ```bash
    python app.py
    ```
2.  The script will check for required libraries and then launch the Gradio web server. It will print a local URL (usually `http://127.0.0.1:7860` or similar).
3.  **Open the URL** in your web browser.
4.  **Tab 1: Upload & Initial Analysis**
    *   Click the upload area or drag & drop your CSV/XLSX/XLS file.
    *   View the status, raw data preview (optional accordion), data profile, and initial plots.
5.  **Tab 2: Configure Cleaning Steps**
    *   Select the columns you want to keep from the checklist.
    *   Configure the desired cleaning options (checkboxes, radio buttons, text inputs). Adjust the null threshold slider if needed.
    *   Select any date columns you wish to standardize.
    *   Click the **"Apply Cleaning & View Results"** button.
6.  **Tab 3: View & Download Results**
    *   The application will switch to this tab automatically after processing.
    *   Review the detailed Processing Log & Summary.
    *   Inspect the Cleaned Data Table.
    *   View plots for the cleaned data distributions.
    *   Use the "Download Center" buttons to download the cleaned data and any removed duplicate rows (if applicable).
    *   Expand the accordions to view the specific rows removed due to duplication.
    *   Use the "Hide Results & Logs" button if desired.
7.  **Reset:** Use the global "Reset Application State" button at the bottom to clear all inputs, outputs, and loaded data.
8.  **Stop the Server:** Press `Ctrl+C` in the terminal where you ran `python app.py`.

Try the included `sample_data.csv` to see the cleaning features in action!

## 🔧 Configuration

The standardized cleaning rules (e.g., regex for removing characters from phone numbers or emails) are defined in the `DEFAULT_CLEANING_RULES` list within `app.py`. You can modify this list directly in the script if you need to adjust the keywords or regular expressions for your specific use case.

## 🤝 Contributing

Contributions are welcome! If you find a bug or have a feature request, please open an issue on the GitHub repository. If you'd like to contribute code, please fork the repository and submit a pull request.

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
