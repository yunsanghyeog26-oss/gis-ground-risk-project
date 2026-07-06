# GIS 기반 지반 안정성 평가 및 도시계획 의사결정 모델

이 프로젝트는 Python과 GIS 공간 분석을 활용하여 지역별 지반 안정성 위험도를 계산하고, 위험도에 따라 적합한 토지 이용 방향을 추천하는 탐구용 의사결정 모델이다.

중요: 이 결과는 실제 건축 가능 여부나 지반 안전성을 확정하는 공학 판정이 아니다. 고등학교 탐구 활동을 위한 GIS 기반 비교 모델이며, 실제 개발에는 현장 조사, 시추 자료, 전문가 검토가 필요하다.

## 프로젝트 구조

```text
.
├─ main.py
├─ config.py
├─ utils.py
├─ risk_model.py
├─ visualize.py
├─ requirements.txt
├─ run_project.ps1
├─ report_draft.md
├─ data/
│  └─ raw/
│     ├─ region.shp
│     ├─ fault.shp
│     ├─ geology.shp
│     ├─ soil.shp
│     ├─ groundwater.shp 또는 groundwater.csv
│     ├─ slope.tif
│     └─ weathering.shp
└─ outputs/
   ├─ final_result.geojson
   ├─ final_result.csv
   ├─ risk_map.html
   └─ risk_grade_summary.png
```

Shapefile은 `.shp` 하나만으로 작동하지 않는다. `.shp`, `.shx`, `.dbf`, `.prj` 파일을 같은 폴더에 함께 넣어야 한다.

## 사용 데이터

| 파일 | 의미 | 처리 방식 |
|---|---|---|
| `region.shp` | 행정구역 또는 분석 격자 | 모든 결과를 집계하는 기준 단위 |
| `fault.shp` | 단층 분포 | 지역과 단층의 교차 여부 또는 거리로 위험 점수 계산 |
| `geology.shp` | 지질 및 암석 종류 | 지역과 중첩되는 대표 암석 종류 선택 |
| `soil.shp` | 토질 | 지역과 중첩되는 대표 토질 선택 |
| `groundwater.shp` / `groundwater.csv` | 지하수위 또는 지하수면 깊이 | 지역별 평균값 계산 |
| `slope.tif` | 경사도 래스터 | 지역별 평균 경사도 추출 |
| `weathering.shp` | 풍화 정도 | 지역별 대표 풍화 등급 선택 |

현재 로컬 실행에서는 `C:\Users\jong8770\Downloads\jiban_strata_WGS84_shp\jiban_strata_WGS84.shp` 자료를 토질 및 지하수 예시 자료로 사용하도록 설정되어 있다. 이 자료에는 `USCS_NM`, `CIVIL_NM`, `GWL_M` 같은 속성이 포함되어 있다.

## 알고리즘 원리

1. 모든 공간 데이터를 같은 좌표계(`EPSG:5179`)로 변환한다.
2. `region.shp`가 있으면 이를 분석 기준 단위로 사용한다.
3. `region.shp`가 없고 시추 지층 자료가 있으면 자료의 분포 범위를 기준으로 자동 격자를 만든다.
4. 벡터 자료는 공간 결합 또는 중첩 분석으로 지역별 대표 속성을 추출한다.
5. 래스터 자료인 `slope.tif`는 지역별 평균 경사도 값을 추출한다.
6. 각 요소별 위험 점수를 0~100점으로 계산한다.
7. 가중합으로 최종 위험도 점수를 계산한다.
8. 점수 구간에 따라 위험도 등급과 추천 토지 이용 방향을 부여한다.

기본 가중치:

```text
final_risk_score =
fault_score * 0.25 +
geology_score * 0.20 +
soil_score * 0.20 +
groundwater_score * 0.15 +
slope_score * 0.10 +
weathering_score * 0.10
```

자료가 일부만 있을 경우, 사용 가능한 요소의 가중치만 다시 합산하여 100%가 되도록 재정규화한다. 그래서 현재처럼 토질과 지하수 자료만 있는 상황에서도 실행이 가능하다.

## 위험도 등급

| 코드 | 보고서 표현 | 점수 범위 |
|---|---|---|
| `very_low` | 매우 낮음 | 0 이상 15 미만 |
| `low` | 낮음 | 15 이상 30 미만 |
| `slightly_low` | 약간 낮음 | 30 이상 45 미만 |
| `moderate` | 보통 | 45 이상 60 미만 |
| `high` | 높음 | 60 이상 75 미만 |
| `very_high` | 매우 높음 | 75 이상 90 미만 |
| `extreme` | 극히 높음 | 90 이상 100 이하 |

## 토지 이용 추천

| 등급 | 추천 방향 |
|---|---|
| 매우 낮음 | 표준 지반 조사 후 고밀도 개발 검토 가능 |
| 낮음 | 주거지, 공공시설, 산업단지 검토 가능 |
| 약간 낮음 | 일반 주거지, 학교, 중소형 공공시설 검토 가능 |
| 보통 | 중저밀도 이용 권장, 추가 지반 조사 필요 |
| 높음 | 저층 건물, 공원, 녹지, 완충지대 권장 |
| 매우 높음 | 대규모 개발 제한, 방재시설 또는 녹지 활용 권장 |
| 극히 높음 | 개발 회피 또는 엄격한 관리, 생태녹지와 방재 목적 활용 권장 |

## 실행 방법

PowerShell에서 프로젝트 폴더로 이동한 뒤 다음 명령을 실행한다.

```powershell
.\run_project.ps1
```

일반 Python 환경에서 실행하려면 다음 순서로 실행한다.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

GeoPandas 또는 Rasterio 설치가 실패하면 Anaconda/Miniconda 환경에서 다음 명령을 사용하는 것이 안정적이다.

```bash
conda install -c conda-forge geopandas rasterio folium matplotlib pandas shapely pyogrio rtree
```

## 결과 파일

| 파일 | 설명 |
|---|---|
| `outputs/final_result.geojson` | 지역별 위험 점수, 위험도 등급, 추천 토지 이용을 포함한 공간 데이터 |
| `outputs/final_result.csv` | 지역명, 요소별 점수, 최종 점수, 등급, 추천 내용을 담은 표 |
| `outputs/risk_map.html` | Folium으로 만든 위험도 시각화 지도 |
| `outputs/risk_grade_summary.png` | 위험도 등급별 지역 수를 보여 주는 그래프 |

## 코드 파일 설명

| 파일 | 역할 |
|---|---|
| `main.py` | 전체 분석 흐름 실행 |
| `config.py` | 파일 경로, 속성명, 가중치, 등급 기준 관리 |
| `utils.py` | 좌표계 변환, 공간 결합, 격자 생성, 래스터 평균 추출 |
| `risk_model.py` | 요소별 점수화, 최종 위험도 계산, 등급 분류 |
| `visualize.py` | Folium 지도와 Matplotlib 그래프 생성 |

## 한계점

- 현재 결과는 탐구용 모델이며 실제 지반 안정성 판정이 아니다.
- 자료의 정확도, 최신성, 좌표계, 속성명에 따라 결과가 달라질 수 있다.
- 단층, 지질, 경사도, 풍화 정도 자료가 누락되면 해당 요소는 계산에서 제외된다.
- 토질과 지하수 위험 점수 기준은 예시 기준이므로 문헌 조사나 전문가 기준에 따라 보정해야 한다.
- 실제 도시계획에서는 법적 규제, 토지 이용 현황, 인구, 교통, 환경 영향도 함께 고려해야 한다.
