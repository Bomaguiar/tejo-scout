import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scanner'))
from scan import extract, number, match_duplicate, validate_catalog, lifecycle

def page(title,desc,price=100000,area=50,address='Mafra',kind='House'):
    import json
    obj={'@type':kind,'name':title,'description':desc,'address':{'addressLocality':address},'offers':{'price':price,'priceCurrency':'EUR','businessFunction':'Sell'},'floorSize':{'value':area}}
    return '<html><h1>'+title+'</h1><script type="application/ld+json">'+json.dumps(obj)+'</script></html>'

class ScannerTests(unittest.TestCase):
    def test_sold_badge_excluded(self):
        self.assertEqual(lifecycle('<h1>Moradia</h1><span class="property-status">Vendido</span>')[0],'sold')
    def test_reserved_badge_excluded(self):
        self.assertEqual(lifecycle('<h1>Moradia</h1><span data-property-status="Reservado"></span>')[0],'reserved')
    def test_related_sold_property_not_evidence(self):
        self.assertIsNone(lifecycle('<h1>Moradia</h1><footer>Imóveis vendidos</footer><div class="related">Casa vendida</div>')[0])
    def test_explicit_primary_offer_status(self):
        self.assertEqual(lifecycle('<script type="application/ld+json">{"@type":"RealEstateListing","offers":{"availability":"https://schema.org/SoldOut"}}</script>')[0],'sold')
    def test_house_with_land_is_not_land_listing(self):
        r=extract(page('Moradia com terreno para recuperar','170 m2 de área bruta de construção; terreno com 450 m2',area=170),'https://agency.pt/mafra/casa')
        self.assertEqual(r['kind'],'house');self.assertEqual(r['area'],170)
    def test_full_district_municipalities(self):
        r=extract(page('Moradia Barreiro para recuperar','Precisa de recuperação',address='Barreiro'),'https://agency.pt/barreiro/casa')
        self.assertEqual(r['municipality'],'Barreiro')
    def test_finished_remodel_is_not_a_renovation_project(self):
        with self.assertRaises(ValueError):extract(page('Moradia T2','Totalmente remodelado, pronto a habitar'),'https://agency.pt/mafra/casa')
    def test_heat_recovery_and_nearby_works_not_renovation(self):
        for desc in ['Moradia nova com recuperador de calor','Perto da estação em remodelação','Totalmente recuperado e pronto a habitar']:
            with self.assertRaises(ValueError):extract(page('Moradia T2',desc),'https://agency.pt/mafra/casa')
    def test_portuguese_amounts(self):
        for text,value in [('1.250.000 €',1250000),('162,76 m²',162.76),('270.8900',270.89),('59 900',59900)]:self.assertEqual(number(text),value)
    def test_renovation_home_uses_floor_area(self):
        r=extract(page('Moradia para recuperar','Terreno com 2000 m²; casa por recuperar',area=54),'https://agency.pt/mafra/casa')
        self.assertEqual(r['area'],54);self.assertEqual(r['municipality'],'Mafra')
    def test_no_floor_area_cannot_use_land_area(self):
        with self.assertRaises(ValueError):extract(page('Moradia para recuperar','Terreno com 2000 m²',area=None),'https://agency.pt/mafra/casa')
    def test_location_not_distance_from_description(self):
        with self.assertRaises(ValueError):extract(page('Moradia para recuperar','A 10 km de Mafra',address='Porto'),'https://agency.pt/porto/casa')
    def test_beach_proximity_and_river_not_sea_view(self):
        for desc in ['A 300 metros da praia','Vista para o rio Tejo','Sem vista mar','Futura vista mar após construir']:
            with self.assertRaises(ValueError):extract(page('Terreno em Mafra',desc+'; terreno com 1000 m²',kind='RealEstateListing'),'https://agency.pt/mafra/terreno')
    def test_partial_sea_view(self):
        r=extract(page('Terreno Mafra','Vista parcial de mar; terreno com 1000 m²',kind='RealEstateListing'),'https://agency.pt/mafra/terreno')
        self.assertEqual(r['view'],'Partial');self.assertEqual(r['area'],1000)
    def test_rental_excluded(self):
        with self.assertRaises(ValueError):extract(page('Moradia para arrendar','Para recuperar'),'https://agency.pt/mafra/casa')
    def test_wrong_advert_schema_rejected(self):
        html=page('Moradia para recuperar','Para recuperar').replace('"@type": "House"','"url":"https://agency.pt/other","@type": "House"')
        with self.assertRaises(ValueError):extract(html,'https://agency.pt/mafra/casa')
    def test_reference_duplicate_preserves_id(self):
        p={'id':'land-old','sourceURL':'https://portal.pt/ad','municipality':'Mafra','area':1000,'note':'Reference: MTL3208'}
        obs={'sourceURL':'https://agency.pt/ad','reference':'MTL3208','municipality':'Mafra','area':1000}
        self.assertEqual(match_duplicate(obs,[p])[0]['id'],'land-old')

if __name__=='__main__':unittest.main()
