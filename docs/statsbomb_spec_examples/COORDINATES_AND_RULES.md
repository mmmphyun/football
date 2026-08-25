# StatsBomb  &    

## 1.   (Coordinate System)

* ** **: $120.0 \times 80.0$ (: /  )
  - $x$ : $0.0 \sim 120.0$ ($0$:  , $120$:  )
  - $y$ : $0.0 \sim 80.0$ ($0$:   , $80$:   )
  -  : $x=0, y=40$ ( ), $x=120, y=40$ ( )
  -  : $x \le 18$  $x \ge 102$ ($y: 18 \sim 62$)

```
 (0,0)                                              (120,0)
   
                                                     
                                    
      (18)                              (102)   
                      (60,40)               
(0,40)  (0)                 +            (120)    (120,40)
[]                                          []
                                            
                                                
                                    
                                                     
   
 (0,80)                                             (120,80)
```

> **[]     !**
> StatsBomb      ** ($x=0$) ($x=120$) **  .

---

## 2. 3(Thirds)  

* **Defensive Third ( 3)**: $0.0 \le x < 40.0$
* **Middle Third ( 3)**: $40.0 \le x < 80.0$
* **Final Third / Attacking Third ( 3)**: $80.0 \le x \le 120.0$

---

## 3. 12x8   (Grid Zones)

*  12 (1 $10.0\text{m}$),  8 (1 $10.0\text{m}$)
* `col = min(11, max(0, int(x * 12 / 120)))`
* `row = min(7, max(0, int(y * 8 / 80)))`
* / (`possession`, `out_of_possession`)   :
  $$\text{Cell Occupancy} = \frac{\text{     }}{\text{ /    }}$$

---

## 4.  (Time)  

* `minute` `second`  1/1     .
* (`period=1`): `0:00` ~ `45:00` (+ )
* (`period=2`): `45:00` ~ `90:00` (+ )
* **   ()**:
  $$\text{duration\_min} = \max(\text{events.minute}) \approx 90 \sim 100\text{}$$
  *(  `(period - 1) * 3600`    60   150   )*

---

## 5. 360    

360   ID .       :

|   | 360    |
| :--- | :--- |
| ** (Formation)** |     **  (ID )**  , 360      |
| **  (Zones)** | `teammate`   /     |
| ** ** | `actor=True`    `player_id` , `keeper=True` ,      /  |
| **  (Predict)** |          $\to$ $+2$ ( ) |
