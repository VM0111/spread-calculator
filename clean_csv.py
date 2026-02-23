import os

FILES_TO_CLEAN = [
    "futures_distribution.csv",
    "spot_distribution.csv",
    "futures_distribution_XAGUSD.csv",
    "spot_distribution_XAGUSD.csv"
]

def clean_range_string(val):
    val = str(val).replace('(', '').replace(']', '').replace('[', '').replace(')', '').replace('"', '').replace("'", "").strip()
    parts = val.replace(',', ' ').split()
    if len(parts) == 2:
        return f"{parts[0]} - {parts[1]}"
    return val

def clean_all():
    """Funkcja odpalana przez app.py, czyści pliki w locie na serwerze."""
    for filename in FILES_TO_CLEAN:
        if not os.path.exists(filename):
            continue
            
        cleaned_lines = []
        try:
            with open(filename, 'r', encoding='utf-8-sig') as f:
                lines = [line.strip() for line in f if line.strip()]
                
            if not lines:
                continue
                
            sep = ";" if ";" in lines[0] else ","
            cleaned_lines.append(f"volume_range{sep}filled_volume")
            
            for line in lines[1:]:
                last_sep_idx = line.rfind(sep)
                if last_sep_idx != -1:
                    vol_range = line[:last_sep_idx].strip()
                    filled_vol = line[last_sep_idx+1:].strip()
                    
                    clean_vol_range = clean_range_string(vol_range)
                    cleaned_lines.append(f"{clean_vol_range}{sep}{filled_vol}")
                    
            new_filename = filename.replace(".csv", "_clean.csv")
            with open(new_filename, 'w', encoding='utf-8-sig') as f:
                for line in cleaned_lines:
                    f.write(line + "\n")
                    
        except Exception as e:
            print(f"Błąd podczas czyszczenia {filename}: {e}")

# Umożliwia odpalenie skryptu także ręcznie w konsoli
if __name__ == "__main__":
    clean_all()