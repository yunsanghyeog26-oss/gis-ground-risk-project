# data/raw 폴더 안내

이 폴더에는 실제 GIS 원본 데이터를 넣는다.

예시 파일명:

- `region.shp`: 행정구역 또는 분석 격자
- `fault.shp`: 단층 데이터
- `geology.shp`: 지질 및 암석 종류
- `soil.shp`: 토질 데이터
- `groundwater.shp` 또는 `groundwater.csv`: 지하수 데이터
- `slope.tif`: 경사도 래스터
- `weathering.shp`: 풍화 정도

Shapefile은 `.shp`, `.shx`, `.dbf`, `.prj` 파일을 모두 같은 폴더에 넣어야 한다.

현재 `config.py`는 예시 실행을 위해 다운로드 폴더의 다음 자료도 읽도록 설정되어 있다.

```text
C:\Users\jong8770\Downloads\jiban_strata_WGS84_shp\jiban_strata_WGS84.shp
```

