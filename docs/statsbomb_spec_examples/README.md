# StatsBomb Open Data     

  StatsBomb Open Data 5                .

---

##    

1. **`01_competitions.json`** —     (`match_available_360` 360   )
2. **`02_matches.json`** —  /     360  (`match_status_360`)
3. **`03_lineups.json`** —   , ,    (`positions`)
4. **`04_events.json`** —     (, , , ,  ,  )
5. **`05_three_sixty.json`** — 360   (`event_uuid` ,   , `teammate`/`actor`/`keeper`)
6. **`COORDINATES_AND_RULES.md`** —  ,  , 360    

---

##   :     4 

### 1.   (  →  )
```
  y=0 ( )
   
    [ ]             []             [ ]  
    (Defensive Third)   (Middle Third)      (Final Third)  
                                                           
x=0                                      x=120
                                                           
      0 <= x < 40         40 <= x < 80         80 <= x <=120
   
  y=80 ( )
```
* **   /   **: StatsBomb    **     x=0 x=120  **   .
*  `attack_direction`   -1     .

---

### 2. 360  vs    
* **  (`events/{id}.json`)**: 
  -    /  .
  -   (`player.id`), (`pass.recipient.id`)  **  **.
* **360  (`three-sixty/{id}.json`)**: 
  -     (`visible_area`)   **    **.
  - `event_uuid`   `id` 1:1 .
  - ** ID  ()**: `{ "teammate": bool, "actor": bool, "keeper": bool, "location": [x, y] }`  .

---

### 3.    
* **(Goal)**:     (   30  ) ~    ( 4)
* **(Shot, xG >= 0.25)**:     (   15  ) ~    ( 4)

---

### 4. /  (PPDA) 
* PPDA = (    [  x >= 40]) / (     [x >= 40])
*  : `Pressure`, `Tackle`, `Interception`, `Block`, `Clearance`
