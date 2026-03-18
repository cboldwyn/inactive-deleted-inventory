"""
Inactive & Deleted Product Inventory Check v1.0.0
Flags Inactive or Deleted Blaze product profiles that still have inventory.

Upload Company Products CSV to check for Inactive profiles with inventory.
Upload Products Deleted CSV to check for Deleted profiles with inventory.

CHANGELOG:
v1.0.0 (2026-03-17)
- Initial release
- Two-tab layout: Inactive Products, Deleted Products
- CSV upload with Blaze title-row handling
- Filters for non-zero inventory across all INV columns
- Summary metrics, sortable results table, CSV export
"""

import streamlit as st
import pandas as pd
import io

# ============================================================================
# CONFIGURATION
# ============================================================================

VERSION = "1.0.0"

st.set_page_config(
    page_title=f"Inventory Check v{VERSION}",
    page_icon="🔍",
    layout="wide"
)

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def load_blaze_csv(uploaded_file):
    """
    Load a Blaze CSV export, skipping the title row.

    Blaze CSVs have a report title on line 1 and headers on line 2.

    Args:
        uploaded_file: Streamlit UploadedFile object

    Returns:
        pd.DataFrame: Parsed CSV data with correct headers
    """
    lines = uploaded_file.read().decode("utf-8-sig", errors="replace").splitlines()
    return pd.read_csv(io.StringIO("\n".join(lines[1:])), low_memory=False)


def get_inv_columns(df):
    """Return list of INV: prefixed columns from a DataFrame."""
    return [c for c in df.columns if c.startswith("INV:")]


def to_numeric_safe(df, columns):
    """Convert columns to numeric, coercing errors to 0."""
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df

# ============================================================================
# PROCESSING FUNCTIONS
# ============================================================================

def process_inactive(df):
    """
    Filter Company Products for Inactive profiles with inventory.

    Args:
        df (pd.DataFrame): Raw Company Products export

    Returns:
        tuple: (filtered DataFrame, list of active INV columns)
    """
    inv_cols = get_inv_columns(df)
    df = to_numeric_safe(df, inv_cols + ["Inventory Available"])

    inactive = df[
        (df["Active"].str.strip().str.lower() == "no") &
        (df["Inventory Available"] > 0)
    ].copy()

    active_inv_cols = [c for c in inv_cols if inactive[c].sum() > 0]
    return inactive, active_inv_cols


def process_deleted(df):
    """
    Filter Deleted Products for profiles with inventory.

    Args:
        df (pd.DataFrame): Raw Deleted Products export

    Returns:
        pd.DataFrame: Filtered to rows with Available Inventory > 0
    """
    df = to_numeric_safe(df, ["Available Inventory"])
    return df[df["Available Inventory"] > 0].copy()

# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    st.title(f"🔍 Inventory Check v{VERSION}")
    st.markdown("Flag Inactive or Deleted Blaze profiles that still have inventory.")

    # ── Sidebar ──
    st.sidebar.header("📂 Upload Files")
    file_cp = st.sidebar.file_uploader(
        "Company Products CSV",
        type=["csv"],
        key="cp",
        help="Blaze Company Products export. Used to find Inactive profiles with inventory."
    )
    file_dp = st.sidebar.file_uploader(
        "Deleted Products CSV",
        type=["csv"],
        key="dp",
        help="Blaze Deleted Products export. Used to find Deleted profiles with inventory."
    )

    with st.sidebar.expander("📋 Version History & Changelog"):
        st.markdown("""
        **v1.0.0** (2026-03-17)
        - Initial release
        - Inactive and Deleted product checks
        - CSV export for results
        """)

    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**Version {VERSION}**")

    # ── Tabs ──
    tab1, tab2 = st.tabs(["📊 Inactive Products", "🗑️ Deleted Products"])

    # ── Inactive Products Tab ──
    with tab1:
        if not file_cp:
            st.info("Upload a Company Products CSV in the sidebar to check for Inactive products with inventory.")
        else:
            df_cp = load_blaze_csv(file_cp)
            inactive, active_inv_cols = process_inactive(df_cp)

            # Metrics
            total_products = len(df_cp)
            total_inactive = len(df_cp[df_cp["Active"].str.strip().str.lower() == "no"])
            flagged = len(inactive)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Products", f"{total_products:,}")
            with col2:
                st.metric("Total Inactive", f"{total_inactive:,}")
            with col3:
                st.metric("Inactive with Inventory", f"{flagged:,}")

            if inactive.empty:
                st.success("✅ No inactive products with inventory found.")
            else:
                st.warning(f"⚠️ **{flagged} inactive products still have inventory.**")

                display_cols = ["Shop", "SKU", "Item", "Category", "Brand", "Vendor", "Inventory Available"]
                display_cols.extend(active_inv_cols)
                available = [c for c in display_cols if c in inactive.columns]

                result = inactive[available].sort_values(
                    "Inventory Available", ascending=False
                ).reset_index(drop=True)

                st.dataframe(result, use_container_width=True, hide_index=True)

                csv_out = result.to_csv(index=False)
                st.download_button(
                    "📥 Download Inactive Report",
                    csv_out,
                    file_name="inactive_products_with_inventory.csv",
                    mime="text/csv"
                )

    # ── Deleted Products Tab ──
    with tab2:
        if not file_dp:
            st.info("Upload a Deleted Products CSV in the sidebar to check for Deleted products with inventory.")
        else:
            df_dp = load_blaze_csv(file_dp)
            deleted_inv = process_deleted(df_dp)

            # Metrics
            total_deleted = len(df_dp)
            flagged_del = len(deleted_inv)

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Deleted Products", f"{total_deleted:,}")
            with col2:
                st.metric("Deleted with Inventory", f"{flagged_del:,}")

            if deleted_inv.empty:
                st.success("✅ No deleted products with inventory found.")
            else:
                st.warning(f"⚠️ **{flagged_del} deleted products still have inventory.**")

                display_cols = ["Shop Name", "SKU", "Item", "Category", "Brand", "Vendor",
                               "Available Inventory", "Product ID", "Modified"]
                available = [c for c in display_cols if c in deleted_inv.columns]

                result = deleted_inv[available].sort_values(
                    "Available Inventory", ascending=False
                ).reset_index(drop=True)

                st.dataframe(result, use_container_width=True, hide_index=True)

                csv_out = result.to_csv(index=False)
                st.download_button(
                    "📥 Download Deleted Report",
                    csv_out,
                    file_name="deleted_products_with_inventory.csv",
                    mime="text/csv"
                )


if __name__ == "__main__":
    main()
