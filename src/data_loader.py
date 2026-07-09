import pandas as pd
import json


"""module qui charge le dataset et construit le contexte que Claude va recevoir à chaque question"""
def load_superstore(filepath: str) -> pd.DataFrame:
    """Charge le dataset Superstore."""
    df = pd.read_csv(filepath, encoding='latin-1')
    # Convertit la date
    df['Order Date'] = pd.to_datetime(df['Order Date'])
    df['Ship Date'] = pd.to_datetime(df['Ship Date'])
    return df


def get_schema(df: pd.DataFrame) -> dict:
    """
    Retourne le schéma complet du dataset.
    C'est ce que Claude recoit pour comprendre les données disponibles.
    """
    schema = {
        "name": "Superstore Sales",
        "description": "Dataset de ventes US d'une chaine de distribution, 2015-2018",
        "nb_rows": len(df),
        "nb_columns": len(df.columns),
        "columns": {}
    }

    for col in df.columns:
        schema["columns"][col] = {
            "type": str(df[col].dtype),
            "nb_unique": int(df[col].nunique()),
            "sample_values": df[col].dropna().unique()[:5].tolist()
        }

    return schema


def get_quick_stats(df: pd.DataFrame) -> dict:
    """Stats rapides pour le dashboard de l'interface."""
    return {
        "nb_orders": df['Order ID'].nunique(),
        "nb_customers": df['Customer ID'].nunique(),
        "nb_products": df['Product ID'].nunique(),
        "total_sales": round(df['Sales'].sum(), 2),
        "total_profit": round(df['Profit'].sum(), 2),
        "date_range": f"{df['Order Date'].min().strftime('%Y-%m-%d')} - {df['Order Date'].max().strftime('%Y-%m-%d')}",
        "regions": df['Region'].unique().tolist(),
        "categories": df['Category'].unique().tolist()
    }


def schema_to_prompt(schema: dict) -> str:
    """
    Convertit le schema en texte lisible par Claude.
    Utilisé dans le system prompt de l'agent.
    """
    lines = [
        f"Dataset : {schema['name']}",
        f"Description : {schema['description']}",
        f"Dimensions : {schema['nb_rows']} lignes x {schema['nb_columns']} colonnes",
        "",
        "Colonnes disponibles :"
    ]

    for col_name, col_info in schema['columns'].items():
        samples = ', '.join([str(v) for v in col_info['sample_values'][:3]])
        lines.append(
            f"  - {col_name} ({col_info['type']}, {col_info['nb_unique']} valeurs uniques) "
            f"ex: {samples}"
        )

    return '\n'.join(lines)