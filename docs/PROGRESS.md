#    (2026-08-25 v3  )

StatsBomb Open Data     `IMPLEMENTATION_PLAN_V3.md`   .

---

##     

|  |    |  |
| :--- | :--- | :---: |
| **0:   ** |   3 ,   , v3   | ** ** |
| **1:  ** | `config.py`, `downloader.py` (/), `storage.py` (CRUD) | ** ** |
| **2:   ** | `common.py`, `formation.py`, `zones.py`, `passes.py`, `pressure.py`, `buildup.py`, `transitions.py`, `predict.py` | ** ** |
| **3:  & ** | `highlights.py`, `frames.py`, `processing.py`, `cli.py`, `main.py` (FastAPI) | ** ** |
| **4:  ** |    pytest /   | ** ** |
| **5:  ** | React 18 + TS + Tailwind + D3  ,  ,   | ** ** |
| **6:   & ** |  360   fetch -> process -> UI , Docker Compose | ** ** |

---

##    

### 1:  
- [ ] `backend/app/config.py`: /  
- [ ] `backend/app/downloader.py`: `match_available_360`   & `data/raw/`  
- [ ] `backend/app/storage.py`: SQLite   CRUD  

### 2:   
- [ ] `backend/app/analysis/common.py`:    (`attack_direction` ),   
- [ ] `backend/app/analysis/formation.py`:       
- [ ] `backend/app/analysis/zones.py`: 360    12x8  
- [ ] `backend/app/analysis/passes.py`:   /  
- [ ] `backend/app/analysis/pressure.py`:  (x>=40) PPDA    
- [ ] `backend/app/analysis/buildup.py`: 3     /
- [ ] `backend/app/analysis/transitions.py`:    8  / 
- [ ] `backend/app/analysis/predict.py`: +2   (/ ,  )

### 3:  & 
- [ ] `backend/app/highlights.py`:   xG>=0.25  +   
- [ ] `backend/app/frames.py`: 360 ///  
- [ ] `backend/app/processing.py`:     DB  
- [ ] `backend/app/cli.py`: `fetch`, `process` CLI 
- [ ] `backend/app/main.py`: FastAPI REST API 5  CORS

### 4:  
- [ ] `backend/tests/fixtures/`:  
- [ ] `backend/tests/test_analysis.py`, `test_highlights.py`, `test_api.py`

### 5:  
- [ ] Vite + React 18 + TS + Tailwind 
- [ ] `src/lib/pitch.ts`, `predict.ts`, `interpolate.ts`
- [ ] `TacticalBoard.tsx` (D3 SVG ,  , , , 22  )
- [ ] `MatchView.tsx`, `HighlightView.tsx`, `App.tsx`

---

##      
1. ****:    x=0 -> x=120  ( ).
2. **360 **: `event_uuid` ,   (`actor`= , `keeper`=GK, = ).
3. ** **: `visible_area`   .
4. **22 **:    +      .
