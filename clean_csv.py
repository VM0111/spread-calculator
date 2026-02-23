import os

FILES_TO_CLEAN = [
    "futures_distribution.csv",
    "spot_distribution.csv",
    "futures_distribution_XAGUSD.csv",
    "spot_distribution_XAGUSD.csv"
]

def clean_range_string(val):
    """
    Czyści surowy ciąg znaków przedziału, np. '(20.1, 30.5]' -> '20.1 - 30.5'.
    Zaprojektowane tak, by nie psuć liczb zmiennoprzecinkowych.
    """
    if not val or str(val).lower() == 'nan':
        return "0 - 0"

    # 1. Usuwamy nawiasy i cudzysłowy (pozostawiając kropki i przecinki wewnątrz)
    val = str(val).replace('(', '').replace(']', '').replace('[', '').replace(')', '').replace('"', '').replace("'", "").strip()
    
    # 2. Dzielimy po przecinku, który separuje dwie liczby w przedziale
    # Używamy split(','), co jest bezpieczniejsze niż zamiana wszystkiego na spacje
    parts = [p.strip() for p in val.split(',') if p.strip()]
    
    # 3. Logika łączenia w czytelny przedział
    if len(parts) == 2:
        return f"{parts[0]} - {parts[1]}"
    elif len(parts) == 1:
        # Jeśli jest tylko jedna liczba, zwracamy ją bez zmian
        return parts[0]
    
    # 4. Fallback dla nietypowych formatów (np. już sformatowanych z myślnikiem)
    return val

def clean_all():
    """Funkcja czyści pliki wejściowe i tworzy wersje z końcówką _clean.csv."""
    for filename in FILES_TO_CLEAN:
        if not os.path.exists(filename):
            print(f"Pominięto: {filename} (plik nie istnieje)")
            continue
            
        cleaned_lines = []
        try:
            with open(filename, 'r', encoding='utf-8-sig') as f:
                # Wczytujemy linie, ignorując puste
                lines = [line.strip() for line in f if line.strip()]
                
            if not lines:
                continue
                
            # Wykrywamy separator (średnik ma priorytet w polskim Excelu)
            sep = ";" if ";" in lines[0] else ","
            
            # Nagłówek
            cleaned_lines.append(f"volume_range{sep}filled_volume")
            
            for line in lines[1:]:
                # Szukamy ostatniego separatora, aby oddzielić przedział od wartości 'filled_volume'
                last_sep_idx = line.rfind(sep)
                if last_sep_idx != -1:
                    vol_range = line[:last_sep_idx].strip()
                    filled_vol = line[last_sep_idx+1:].strip()
                    
                    # Czyścimy przedział bezpieczną metodą
                    clean_vol_range = clean_range_string(vol_range)
                    cleaned_lines.append(f"{clean_vol_range}{sep}{filled_vol}")
            
            new_filename = filename.replace(".csv", "_clean.csv")
            with open(new_filename, 'w', encoding='utf-8-sig') as f:
                for line in cleaned_lines:
                    f.write(line + "\n")
            
            print(f"Sukces: Utworzono {new_filename}")
                    
        except Exception as e:
            print(f"Błąd podczas czyszczenia {filename}: {str(e)}")

if __name__ == "__main__":
    clean_all()