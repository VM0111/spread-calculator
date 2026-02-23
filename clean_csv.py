import os

# Lista plików, których będziemy szukać w folderze
FILES_TO_CLEAN = [
    "futures_distribution.csv",
    "spot_distribution.csv",
    "futures_distribution_XAGUSD.csv",
    "spot_distribution_XAGUSD.csv"
]

def clean_range_string(val):
    """Usuwa nawiasy, cudzysłowy i zamienia format na START - END"""
    val = str(val).replace('(', '').replace(']', '').replace('[', '').replace(')', '').replace('"', '').replace("'", "").strip()
    # Zamienia przecinki na spacje, żeby zunifikować (0.0 0.1] oraz (0, 0.1]
    parts = val.replace(',', ' ').split()
    if len(parts) == 2:
        return f"{parts[0]} - {parts[1]}"
    return val

print("Rozpoczynam czyszczenie plików CSV...")

for filename in FILES_TO_CLEAN:
    if not os.path.exists(filename):
        print(f"[\u2717] Pominięto {filename} — plik nie istnieje w folderze.")
        continue
        
    cleaned_lines = []
    try:
        with open(filename, 'r', encoding='utf-8-sig') as f:
            lines = [line.strip() for line in f if line.strip()]
            
        if not lines:
            print(f"[\u2717] Plik {filename} jest pusty.")
            continue
            
        # Zgadujemy separator z nagłówka
        sep = ";" if ";" in lines[0] else ","
        
        # Tworzymy nowy, ustandaryzowany nagłówek
        cleaned_lines.append(f"volume_range{sep}filled_volume")
        
        for line in lines[1:]:
            last_sep_idx = line.rfind(sep)
            if last_sep_idx != -1:
                vol_range = line[:last_sep_idx].strip()
                filled_vol = line[last_sep_idx+1:].strip()
                
                clean_vol_range = clean_range_string(vol_range)
                cleaned_lines.append(f"{clean_vol_range}{sep}{filled_vol}")
                
        # Zapis do nowego pliku z przyrostkiem _clean
        new_filename = filename.replace(".csv", "_clean.csv")
        with open(new_filename, 'w', encoding='utf-8-sig') as f:
            for line in cleaned_lines:
                f.write(line + "\n")
                
        print(f"[\u2713] Wyczyszczono i zapisano: {new_filename}")
        
    except Exception as e:
        print(f"[\u2717] Błąd podczas przetwarzania {filename}: {e}")

print("Zakończono! Możesz teraz uruchomić główną aplikację (app.py).")