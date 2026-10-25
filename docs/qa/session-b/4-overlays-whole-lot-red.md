FFF...                                                                   [100%]
================================== FAILURES ===================================
_____ test_point_outside_flood_but_lot_overlaps_reads_flood[8//DP575940] ______

cur = <cursor object at 0x0000026A214B4120; closed: 0>, lot = '8//DP575940'

    @pytest.mark.parametrize("lot", LOTS)
    def test_point_outside_flood_but_lot_overlaps_reads_flood(cur, lot):
        lon, lat = _point(cur, lot)
        cur.execute("SELECT count(*) FROM spatial_overlays WHERE layer_type = 'flood' "
                    "AND ST_Contains(geom, ST_SetSRID(ST_Point(%s, %s), 4326))", (lon, lat))
        assert cur.fetchone()[0] == 0, "fixture no longer valid: the point itself is in a flood polygon"
        cur.execute(_route_sql(), {"lon": lon, "lat": lat})
        layers = [r[0] for r in cur.fetchall()]
>       assert "flood" in layers, f"{lot}: flood overlaps the lot but the route query did not return it"
E       AssertionError: 8//DP575940: flood overlaps the lot but the route query did not return it
E       assert 'flood' in ['lot_size']

tests\test_spatial_overlays_whole_lot_real_db.py:77: AssertionError
_____ test_point_outside_flood_but_lot_overlaps_reads_flood[1//DP854205] ______

cur = <cursor object at 0x0000026A214B4120; closed: 0>, lot = '1//DP854205'

    @pytest.mark.parametrize("lot", LOTS)
    def test_point_outside_flood_but_lot_overlaps_reads_flood(cur, lot):
        lon, lat = _point(cur, lot)
        cur.execute("SELECT count(*) FROM spatial_overlays WHERE layer_type = 'flood' "
                    "AND ST_Contains(geom, ST_SetSRID(ST_Point(%s, %s), 4326))", (lon, lat))
        assert cur.fetchone()[0] == 0, "fixture no longer valid: the point itself is in a flood polygon"
        cur.execute(_route_sql(), {"lon": lon, "lat": lat})
        layers = [r[0] for r in cur.fetchall()]
>       assert "flood" in layers, f"{lot}: flood overlaps the lot but the route query did not return it"
E       AssertionError: 1//DP854205: flood overlaps the lot but the route query did not return it
E       assert 'flood' in ['lot_size']

tests\test_spatial_overlays_whole_lot_real_db.py:77: AssertionError
_____ test_point_outside_flood_but_lot_overlaps_reads_flood[2//DP221940] ______

cur = <cursor object at 0x0000026A214B4120; closed: 0>, lot = '2//DP221940'

    @pytest.mark.parametrize("lot", LOTS)
    def test_point_outside_flood_but_lot_overlaps_reads_flood(cur, lot):
        lon, lat = _point(cur, lot)
        cur.execute("SELECT count(*) FROM spatial_overlays WHERE layer_type = 'flood' "
                    "AND ST_Contains(geom, ST_SetSRID(ST_Point(%s, %s), 4326))", (lon, lat))
        assert cur.fetchone()[0] == 0, "fixture no longer valid: the point itself is in a flood polygon"
        cur.execute(_route_sql(), {"lon": lon, "lat": lat})
        layers = [r[0] for r in cur.fetchall()]
>       assert "flood" in layers, f"{lot}: flood overlaps the lot but the route query did not return it"
E       AssertionError: 2//DP221940: flood overlaps the lot but the route query did not return it
E       assert 'flood' in ['lot_size']

tests\test_spatial_overlays_whole_lot_real_db.py:77: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_spatial_overlays_whole_lot_real_db.py::test_point_outside_flood_but_lot_overlaps_reads_flood[8//DP575940]
FAILED tests/test_spatial_overlays_whole_lot_real_db.py::test_point_outside_flood_but_lot_overlaps_reads_flood[1//DP854205]
FAILED tests/test_spatial_overlays_whole_lot_real_db.py::test_point_outside_flood_but_lot_overlaps_reads_flood[2//DP221940]
3 failed, 3 passed in 1.55s
