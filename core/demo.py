"""Offline demo dataset: a real snapshot of InvestorGain's public GMP, subscription and
GMP-performance reports captured on 25-Sep-2026 (~10:00 IST). Used only when live
fetching is switched off or unreachable, so the dashboard can be explored offline."""
from __future__ import annotations

import pandas as pd

SNAPSHOT = "25-Sep-2026 10:00 IST"
Y = 2026

# name|cat|exchange|status|gmp|gmp_low|gmp_high|fire|sub|price|size_cr|lot|open|close|boa|listing|anchor
_GMP = """
Sollfege Smart Electronics|SME|BSE SME|Upcoming||||1||55|21.78|2000|30-Sep|5-Oct|6-Oct|8-Oct|0
Nityas Gems & Jewellery|Mainboard||Upcoming||0|0|1|||||||||1
Paramount Syntex|SME|BSE SME|Upcoming||0|0|1||127|81.79|1000|30-Sep|6-Oct|7-Oct|9-Oct|0
Omara Ventures India|SME|BSE SME|Upcoming||0|0|1||311|41.99|400|30-Sep|5-Oct|6-Oct|8-Oct|0
Dove Soft|SME|BSE SME|Upcoming||0|0|1||111|73.26|1200|30-Sep|5-Oct|6-Oct|8-Oct|0
EverestIMS Technologies|SME|BSE SME|Upcoming||0|0|1||85|48.46|1600|29-Sep|5-Oct|6-Oct|8-Oct|1
Vans Electroengineerings|SME|BSE SME|Upcoming||0|0|1||118|33.98|1200|29-Sep|1-Oct|5-Oct|7-Oct|1
Papadmalji Agro Foods|SME|NSE SME|Upcoming||0|0|1||72|20.18|1600|29-Sep|1-Oct|5-Oct|7-Oct|0
Black Opal Consultants|SME|BSE SME|Upcoming||0|0|1||197|55.08|600|29-Sep|1-Oct|5-Oct|7-Oct|1
Acme Universal Safezone 9|SME|BSE SME|Upcoming||0|0|1||71|35.93|1600|28-Sep|30-Sep|1-Oct|6-Oct|1
Shivchem Agro|SME|BSE SME|Upcoming||0|0|1||62|14.01|2000|28-Sep|30-Sep|1-Oct|6-Oct|0
SRIT India|Mainboard||Upcoming|22|12|22|3||130|218.40|115|28-Sep|30-Sep|1-Oct|6-Oct|1
Shah Investor's Home|Mainboard||Upcoming|12|10|12|2||167|90.17|85|28-Sep|30-Sep|1-Oct|6-Oct|1
Pind Hospitality|SME|BSE SME|Upcoming||0|0|1||99|17.82|1200|28-Sep|30-Sep|1-Oct|6-Oct|0
Dudani Retail|SME|BSE SME|Open|3|3|3|3||29|10.54|4000|25-Sep|29-Sep|30-Sep|5-Oct|0
Sai Urja Indo|SME|BSE SME|Open||0|0|1||113|24.95|1200|25-Sep|29-Sep|30-Sep|5-Oct|1
Runwal Enterprises|Mainboard||Open|30|17|37|2||305|499.83|49|25-Sep|29-Sep|30-Sep|5-Oct|1
German Green Steel|Mainboard||Open|29|15|29|4||139|303.90|107|25-Sep|29-Sep|30-Sep|5-Oct|1
Acevector|Mainboard||Open|2|2|2|2||32|420.00|468|25-Sep|29-Sep|30-Sep|5-Oct|1
Himalayan Solar|SME|NSE SME|Open||0|0|1||103|68.03|1200|25-Sep|29-Sep|30-Sep|5-Oct|1
Orient Cables|Mainboard||Open|113|34|113|4|0.10|272|552.00|55|25-Sep|29-Sep|30-Sep|5-Oct|1
Bench Mark Infotech Services|SME|NSE SME|Open||0|12|1||110|42.44|1200|25-Sep|29-Sep|30-Sep|5-Oct|1
Shree TNB Polymers|SME|BSE SME|Open||0|0|1||52|31.20|2000|25-Sep|29-Sep|30-Sep|5-Oct|1
Peshwa Wheat|SME|BSE SME|Open||0|0|1|1.82|101|53.52|1200|24-Sep|28-Sep|29-Sep|1-Oct|0
Roopa Screen|SME|BSE SME|Open||0|14|1|1.36|64|19.20|2000|24-Sep|28-Sep|29-Sep|1-Oct|1
Green Asia Impex|SME|NSE SME|Open||0|0|1|0.01|90|60.10|1600|24-Sep|28-Sep|29-Sep|1-Oct|0
Moneyview|Mainboard||Open|15.5|5|15.5|4|1.49|34|1091.68|441|24-Sep|28-Sep|29-Sep|1-Oct|1
A-One Steels|Mainboard||Open|49|49|64|3|0.61|405|405.00|37|24-Sep|28-Sep|29-Sep|1-Oct|1
Adroit Industries|Mainboard||Closing Today|37|32|37|4|18.08|134|150.71|111|23-Sep|25-Sep|28-Sep|30-Sep|1
Core Integra Consulting|SME|NSE SME|Closing Today||0|0|1|0.46|78|21.99|1600|23-Sep|25-Sep|28-Sep|30-Sep|0
Unitec Fibres|SME|BSE SME|Closing Today||0|0|1|0.13|88|34.47|1600|23-Sep|25-Sep|28-Sep|30-Sep|1
Pooja Logistics|SME|NSE SME|Closing Today||0|0|1|0.39|115|44.23|1200|23-Sep|25-Sep|28-Sep|30-Sep|1
Swastika Infra|Mainboard||Closing Today|9|3|9.5|1|1.7|185|160.88|81|23-Sep|25-Sep|28-Sep|30-Sep|1
S.K.Offset|SME|BSE SME|Closing Today||0|0|1|0.34|125|29.06|1000|23-Sep|25-Sep|28-Sep|30-Sep|1
ArMee Infotech|Mainboard||Closing Today|20|1|51|2|1.26|375|300.00|40|23-Sep|25-Sep|28-Sep|30-Sep|1
Elevate Campuses|Mainboard||Closing Today|2.5|2.5|16|1|0.24|362|2100.00|41|23-Sep|25-Sep|28-Sep|30-Sep|1
Liqvd Digital|SME|BSE SME|Closing Today||0|0|1|1.23|54|39.01|2000|23-Sep|25-Sep|28-Sep|30-Sep|0
Himalaya Nutravedics|SME|BSE SME|Closed||0|0|1|2.33|106|26.50|1200|22-Sep|24-Sep|25-Sep|29-Sep|1
Varmora Granito|Mainboard||Closed|0.5|0.5|15|1|1.6|148|708.02|101|22-Sep|24-Sep|25-Sep|29-Sep|1
Anand Seamless|SME|BSE SME|Closed||0|0|1|1.47|72|25.52|1600|22-Sep|24-Sep|25-Sep|29-Sep|0
FX Multitech|SME|BSE SME|Closed|4|4|4|1|17.72|116|45.24|1200|21-Sep|23-Sep|24-Sep|28-Sep|1
Vivekanand Cotspin|SME|BSE SME|Closed||0|0|1|1.79|37|22.20|3000|21-Sep|23-Sep|24-Sep|28-Sep|1
Robokidz Eduventures|SME|BSE SME|Closed|70|45|70|5|833.56|106|31.09|1200|21-Sep|23-Sep|24-Sep|28-Sep|1
Axiom Gas Engineering|SME|NSE SME|Listing Today||0|0|1|1.39|54|50.75|2000|18-Sep|22-Sep|23-Sep|25-Sep|1
"""

# name|cat|total|as_of|qib|shni|bhni|nii|rii|pe|close
_SUB = """
Peshwa Wheat|SME|1.82|24 Sep 17:06|177.12|0.02|0.18|0.13|0.04|8.77|28-09-2026
Roopa Screen|SME|1.36|24 Sep 17:06|0.15|2.19|43.80|4.96|2.89|7.96|28-09-2026
Green Asia Impex|SME|0.01|24 Sep 18:55|0.00|0.01|0.00|0.00|0.03|8.91|28-09-2026
Moneyview|Mainboard|1.49|24 Sep 17:06|0.05|3.36|2.12|2.53|1.87|21.52|28-09-2026
A-One Steels|Mainboard|0.61|24 Sep 17:06|0.10|0.76|0.83|0.81|0.81|21.76|28-09-2026
Adroit Industries|Mainboard|18.08|24 Sep 17:06|1.82|36.54|22.55|27.22|23.45|17.89|25-09-2026
Core Integra Consulting|SME|0.46|24 Sep 18:55|1.05|0.90|0.25|0.46|0.32|13.27|25-09-2026
Unitec Fibres|SME|0.13|24 Sep 17:06|0.00|0.15|0.60|0.43|0.12|12.17|25-09-2026
Pooja Logistics|SME|0.39|24 Sep 18:55|0.00|0.26|0.51|0.26|0.76|9.73|25-09-2026
Swastika Infra|Mainboard|1.7|24 Sep 17:06|1.02|1.54|3.29|2.71|1.66|11.78|25-09-2026
S.K.Offset|SME|0.34|24 Sep 17:06|0.50|0.54|0.28|0.44|0.24|9.06|25-09-2026
ArMee Infotech|Mainboard|1.26|24 Sep 17:05|1.01|1.23|0.77|0.93|1.45|19.57|25-09-2026
Elevate Campuses|Mainboard|0.24|24 Sep 17:05|0.19|0.07|0.49|0.35|0.25|23.03|25-09-2026
Liqvd Digital|SME|1.23|24 Sep 17:06|1.00|0.31|5.66|4.35|0.20|10.74|25-09-2026
Himalaya Nutravedics|SME|2.33|24 Sep 18:55|1.00|3.04|3.84|3.58|2.56|9.04|24-09-2026
Varmora Granito|Mainboard|1.6|24 Sep 18:54|3.10|0.94|0.94|0.94|1.02|54.81|24-09-2026
Anand Seamless|SME|1.47|24 Sep 18:54||||1.96|0.98|11.08|24-09-2026
FX Multitech|SME|17.72|23 Sep 18:54|20.95|18.21|29.94|25.98|12.31|10.86|23-09-2026
Vivekanand Cotspin|SME|1.79|23 Sep 18:55|1.26|1.26|2.99|2.41|1.82|16.30|23-09-2026
Robokidz Eduventures|SME|833.56|23 Sep 18:55|306.73|870.44|1954.28|1593.00|807.12|8.35|23-09-2026
Axiom Gas Engineering|SME|1.39|22 Sep 18:56|1.10|0.92|1.02|0.98|1.86|14.84|22-09-2026
"""

# name|cat|symbol|listing|size|sub|gmp|price|est|listing_price|lp%|day_close|dc%|ltp|ltp%
_PERF = """
Axiom Gas Engineering|SME|AXIOMGAS|25-Sep-26|50.75|1.39|0|54|54|54.75|1.39||||
NSE|Mainboard|544937|24-Sep-26|22561.57|5.71|40|1785|1825|1800|0.84|1818|1.85|1818|1.85
SpectraA Technology Solutions|SME|SPECTRAA|24-Sep-26|42.52|304.06|81|118|199|224.2|90.00|235.4|99.49|235.4|99.49
Kheria Autocomp|SME|KHERIAAUTO|24-Sep-26|46.44|2.48|3|101|104|104.9|3.86|103.05|2.03|103.05|2.03
Sonaselection India|Mainboard|SONA, 544938|24-Sep-26|141.57|2.01|0|99|99|102.31|3.34|107.42|8.51|107.42|8.51
SS Retail|Mainboard|SSRETAIL, 544934|23-Sep-26|500|107.41|160|424|584|624|47.17|765.15|80.46|811.8|91.46
Jindal Supreme|Mainboard|JSIPL, 544935|23-Sep-26|124.88|177.03|29|93|122|120|29.03|127.99|37.62|132.3|42.26
Hero Motors|Mainboard|HEROMOTORS, 544936|23-Sep-26|1000|7.01|-3|84|81|82|-2.38|98.51|17.27|118.08|40.57
Vama Wovenfab|SME|544931|22-Sep-26|49.54|2.53|3|341|344|341|0.00|323.95|-5.00|292.45|-14.24
Shakti Polytarp|SME|544933|22-Sep-26|26.93|11.87|10|59|69|58.9|-0.17|57.08|-3.25|58.39|-1.03
Quanto Agroworld|SME|544932|22-Sep-26|31.02|1.39|0|67|67|66.99|-0.01|63.65|-5.00|63.13|-5.78
Manika Plastech|Mainboard|MANIKA, 544929|21-Sep-26|125.5|29.46|1|43|44|43|0.00|43.14|0.33|41.46|-3.58
Injecto Polymers|SME|544930|21-Sep-26|56.12|1.23|0|100|100|99|-1.00|95.95|-4.05|94|-6
Century Business Media|SME|544928|21-Sep-26|17.11|57.93|0|74|74|74|0.00|73.92|-0.11|72.97|-1.39
Maharaja & Speedex India|SME|544925|18-Sep-26|80.13|32.41|28|186|214|250|34.41|262.5|41.13|260.65|40.13
Raksan Transformers|SME|544924|18-Sep-26|150.5|47.43|12|273|285|273|0.00|286.6|4.98|272.75|-0.09
Panchatv Bharat|SME|544926|18-Sep-26|24.58|1.4|3|140|143|128.95|-7.89|122.55|-12.46|122.55|-12.46
Veegaland Developers|Mainboard|VEEGALAND, 544923|18-Sep-26|210|14.6|8|140|148|154|10.00|146.3|4.50|142.38|1.7
Om Galaxy|SME|544922|18-Sep-26|105|2.07|0|90|90|90.2|0.22|90.77|0.86|89.81|-0.21
Amtech Esters|SME|544920|17-Sep-26|17.88|25.7|16|75|91|100|33.33|105|40.00|108.92|45.23
Manipal Payment and Identity Solutions|Mainboard|MPIMANIPAL, 544916|17-Sep-26|805|1.42|-6|339|333|330|-2.65|345.75|1.99|359.95|6.18
LCC Projects|Mainboard|LCCPROJECT|17-Sep-26|427.14|49.57|36|146|182|189|29.45|170.1|16.51|144.22|-1.22
Steamhouse|Mainboard|STEAMHOUSE, 544914|17-Sep-26|414|32.07|13.5|81|94.5|94.5|16.67|102.55|26.60|113.71|40.38
Vinod Texworld|SME|VINOD|17-Sep-26|42.83|1.6|1|94|95|94|0.00|89.3|-5.00|69.25|-26.33
Rentomojo|Mainboard|RENTOMOJO, 544915|17-Sep-26|1255.57|72.89|87|404|491|482.45|19.42|534.25|32.24|501.9|24.23
Infrax Renewable|SME|544919|17-Sep-26|40.88|2.05|0|104|104|104|0.00|105.5|1.44|118.2|13.65
Asset Reconstruction|Mainboard|ARCIL|17-Sep-26|732.97|20.1|12|139|151|139|0.00|137.02|-1.42|148.62|6.92
Karamtara Engineering|Mainboard|KARAMTARA, 544917|17-Sep-26|875|66.01|46|254|300|320|25.98|352|38.58|369.05|45.3
Glass Wall Systems|Mainboard|GLASSWALL, 544913|16-Sep-26|427.89|81.65|39|182|221|194|6.59|215.35|18.32|272.07|49.49
Prasol Chemicals|Mainboard|PRASOLCHEM, 544912|16-Sep-26|500|3.47|-13|676|663|610|-9.76|672.05|-0.58|720.7|6.61
Kanohar Electricals|Mainboard|KANOHAR, 544911|16-Sep-26|1055.74|90.59|182|632|814|685.5|8.47|751.5|18.91|863.3|36.6
Pranav Constructions|Mainboard|PRANAV, 544909|15-Sep-26|351.03|126.34|53|124|177|165|33.06|132|6.45|100.19|-19.2
Apana Logistics|SME|544910|15-Sep-26|34.14|1.26|0|60|60|60|0.00|57|-5.00|39.83|-33.62
Qualiance International|SME|QUALIANCE|11-Sep-26|45.11|459.22|81|127|208|224.9|77.09|236.1|85.91|191.6|50.87
Deepa Jewellers|Mainboard|DEEPA, 544903|8-Sep-26|459.72|43.4|25|177|202|221|24.86|194.37|9.81|194.18|9.71
Rays of Belief|Mainboard|MOMSBELIEF, 544906|8-Sep-26|125|107.71|15|239|254|239|0.00|228.34|-4.46|222.44|-6.93
Farm Peace|SME|544905|8-Sep-26|32|1.16|59|59|118|112.1|90.00|106.5|80.51|55.54|-5.86
Fly-Hi Maritime|SME|544904|8-Sep-26|52.63|2.12|1|102|103|81.6|-20.00|77.55|-23.97|43.8|-57.06
Ashutosh Fibre|SME|ASHUTOSH|7-Sep-26|56.35|144.65|56|92|148|140|52.17|147|59.78|161.1|75.11
Phychem Technologies|SME|544902|7-Sep-26|14.58|20.79|1|54|55|56|3.70|58.8|8.89|51.73|-4.2
Purple Style Labs|Mainboard|PERNIASPOP, 544901|7-Sep-26|680|1.36|-10|575|565|535|-6.96|568.55|-1.12|530.4|-7.76
Shanti Inorganics|SME|SHANTIINOR|7-Sep-26|47.24|142.17|55|83|138|157.7|90.00|165.55|99.46|175.95|111.99
ESDS Software Solution|Mainboard|ESDS, 544898|4-Sep-26|720|142.88|311|429|740|757|76.46|908.4|111.75|1853.15|331.97
Paluck Technologies|SME|544897|4-Sep-26|33|271.68|9|48|57|46.8|-2.50|49.14|2.38|46.56|-3
Complete Sports and Management|SME|544900|4-Sep-26|74.93|3.45|0|135|135|139|2.96|145.95|8.11|180.95|34.04
Priority Jewels|Mainboard|PRIORITY, 544899|4-Sep-26|91.5|100.45|28|200|228|230|15.00|241.5|20.75|303.99|52
Lumino Industries|Mainboard|LUMINO, 544894|3-Sep-26|700|124.02|38|82|120|110|34.15|110.39|34.62|107.22|30.76
Kwick Forensic Solutions|SME|544895|3-Sep-26|50.77|289|78|90|168|150|66.67|157.5|75.00|178.93|98.81
Annu Projects|Mainboard|ANNU, 544893|2-Sep-26|175.06|2.93|-7|99|92|72|-27.27|77.9|-21.31|49.8|-49.7
Sumax Engineering|SME|SUMAX|2-Sep-26|53.4|162.94|22|101|123|111|9.90|110.45|9.36|108.5|7.43
Symbiotec Pharmalab|Mainboard|SYMBIOTEC, 544889|1-Sep-26|1757|75.08|185|988|1173|988|0.00|1097.7|11.10|1024.05|3.65
Skyways Air|Mainboard|SKYWAYS, 544890|1-Sep-26|582.8|71.25|33|138|171|124|-10.14|125.65|-8.95|131|-5.07
Hy-Tech Engineers|Mainboard|544891|1-Sep-26|135.73|247.39|39|53|92|75|41.51|78.75|48.58|69.41|30.96
Madhur Knit|SME|MADHURKNIT|1-Sep-26|53.27|1.5|2|100|102|100|0.00|95|-5.00|45.9|-54.1
ABH Healthcare|SME|ABH|1-Sep-26|34.98|1.44|0|102|102|99|-2.94|94.05|-7.79|47.75|-53.19
Augmont Enterprises|Mainboard|AUGMONT, 544888|31-Aug-26|825|111.18|290|788|1078|961|21.95|908.15|15.25|864.1|9.66
Tempsens Instruments (India)|Mainboard|TEMPSENS, 544886|28-Aug-26|650|184.22|330|300|630|634|111.33|586.8|95.60|543.4|81.13
Dhanwel Hybrid Seeds|SME|544884|26-Aug-26|26.73|1.65|1|99|100|99|0.00|94.05|-5.00|53.89|-45.57
Gaja Alternative Asset Management|Mainboard|GAJA, 544885|26-Aug-26|550|32.98|18.5|160|178.5|185|15.62|168.7|5.44|145.94|-8.79
Mopshop Distribution|SME|544883|26-Aug-26|27.26|1.59|1|138|139|137|-0.72|130.15|-5.69|44.1|-68.04
Shankesh Jewellers|Mainboard|SHANKESH, 544882|25-Aug-26|367.18|2.8|2.75|93|95.75|103.3|11.08|95.03|2.18|91.51|-1.6
Sunshine Pictures|Mainboard|SUNSHINE, 544881|25-Aug-26|282.14|105.81|50|360|410|395.9|9.97|369.2|2.56|436.9|21.36
Horizon Industrial Parks|Mainboard|HORIZONIND, 544880|24-Aug-26|2600.04|1.52|1.5|60|61.5|60.25|0.42|58.16|-3.07|51.81|-13.65
Lalithaa Jewellery Mart|Mainboard|LALITHAA, 544879|24-Aug-26|1700|66.63|74|201|275|265|31.84|248.44|23.60|370.5|84.33
Fascinate Textiles|SME|FASCINATE|24-Aug-26|64.83|1.48|0|151|151|120.8|-20.00|114.8|-23.97|58.05|-61.56
Technocrats Plasma Systems|SME|544877|21-Aug-26|60.98|203.36|70|132|202|230|74.24|241.5|82.95|382|189.39
ENS Enterprises|SME|544876|21-Aug-26|33.14|13.11|5|92|97|96|4.35|100.8|9.57|101.25|10.05
Skytech Infinite Platform|SME|SKYTECH|21-Aug-26|22.68|2.04|1|77|78|74|-3.90|70.3|-8.70|30.55|-60.32
Credent Connect|SME|CREDENT|20-Aug-26|93.9|153.14|92|189|281|359.1|90.00|377.05|99.50|385.05|103.73
Shiprocket|Mainboard|SHIPROCKET, 544871|19-Aug-26|1617.48|102.28|35|97|132|131|35.05|143.5|47.94|120.46|24.19
Behari Lal Engineering|Mainboard|BLEL, 544870|19-Aug-26|301.62|108.5|133|285|418|465|63.16|502.55|76.33|447.3|56.95
Q&T Foods|SME|544872|19-Aug-26|26.25|1.42|1|115|116|115|0.00|109.25|-5.00|38|-66.96
Pramodini Medicare|SME|PRAMODINI|19-Aug-26|69.04|3.87|0|118|118|120|1.69|121.65|3.09|114.55|-2.92
Milky Mist Dairy Food|Mainboard|MILKYMIST, 544868|18-Aug-26|1553|59.08|19.7|140|159.7|165|17.86|181.5|29.64|309.16|120.83
Sham Foam|SME|544869|18-Aug-26|40.48|2.4|1.5|130|131.5|104|-20.00|98.8|-24.00|76.73|-40.98
Dhoot Transmission|Mainboard|DHOOTTRANS, 544867|17-Aug-26|3066.89|75.06|262|871|1133|1200|37.77|1187.5|36.34|1587.6|82.27
Molbio Diagnostics|Mainboard|MOLBIO, 544866|17-Aug-26|939.7|70.27|116|807|923|980|21.44|1041.7|29.08|1246.2|54.42
Optimystix Entertainment|SME|OPTIMYSTIX|14-Aug-26|108.5|2.05|0|175|175|180|2.86|189|8.00|133.15|-23.91
Technocraft Ventures|Mainboard|TECHNOCRAF, 544864|14-Aug-26|251.88|38.69|42|212|254|284|33.96|311.15|46.77|475.05|124.08
LEAP India|Mainboard|LEAPIND, 544865|14-Aug-26|2480|8.82|13|159|172|165.9|4.34|145.1|-8.74|143.09|-10.01
LAPL Automotive|SME|544863|13-Aug-26|32.4|344.31|50|94|144|135|43.62|128.29|36.48|100|6.38
Ardee Industries|Mainboard|ARDEE, 544860|12-Aug-26|425.87|138.83|17|53|70|72|35.85|67.13|26.66|49.62|-6.38
G.V. Electricals|SME|544859|12-Aug-26|42.25|169.26|25|130|155|158|21.54|165.9|27.62|126.85|-2.42
Aegeus Technologies|SME|544858|11-Aug-26|23.71|29.91|12|105|117|124.5|18.57|130.7|24.48|126.05|20.05
Anawil Wire & Engineering|SME|ANAWIL|10-Aug-26|177.81|149.13|58|270|328|329.65|22.09|346.1|28.19|428.9|58.85
Fusion Klassroom Edutech|SME|544856|7-Aug-26|39.04|1.5|0|159|159|170|6.92|166.75|4.87|176.5|11.01
Juniper Green Energy|Mainboard|JNPR, 544853|6-Aug-26|1800|8.38|23|225|248|245|8.89|259.71|15.43|257.7|14.53
MV Electrosystems|Mainboard|MVELECTRO, 544851|6-Aug-26|290|200.66|109|425|534|520|22.35|624|46.82|818.5|92.59
Dhaval Packaging|SME|544854|6-Aug-26|36.36|49.99|12|97|109|110|13.40|111.68|15.13|123|26.8
Oneindig Technologies|SME|544852|6-Aug-26|27.65|1.73|7|96|103|120|25.00|126|31.25|134|39.58
H.R. Hygiene Products|SME|544848|5-Aug-26|53.95|6.65|1|88|89|90|2.27|87.97|-0.03|61.99|-29.56
Manipal Health Enterprises|Mainboard|MANIPALHOS, 544847|5-Aug-26|9275.22|5.12|7|590|597|652|10.51|666.95|13.04|742.5|25.85
Poojaa Precision Engg.|SME|544844|4-Aug-26|159.83|278.83|200|301|501|470|56.15|493.5|63.95|761.25|152.91
Propshop Events & Exhibitions|SME|PROPSHOP|3-Aug-26|28.57|1.53|0|69|69|55.2|-20.00|57.15|-17.17|71.65|3.84
Advance Technoforge|SME|544843|3-Aug-26|24.04|1.55|4|95|99|94|-1.05|89.3|-6.00|71.43|-24.81
Silverstorm Parks & Resorts|SME|544840|31-Jul-26|82.43|1.91|5|133|138|132.9|-0.08|126.55|-4.85|133.1|0.08
Indo-MIM|Mainboard|INDOMIM, 544837|30-Jul-26|3811.21|72.35|184|485|669|700|44.33|741.8|52.95|1311.15|170.34
Xtranet Technologies|Mainboard|XTRANET, 544838|30-Jul-26|166.8|12.24|14.5|127|141.5|136|7.09|129.2|1.73|313.71|147.02
Lohia Corp|Mainboard|LCL, 544839|30-Jul-26|1101.28|7.26|17|425|442|461|8.47|494.65|16.39|575.55|35.42
"""


def _f(x):
    x = (x or "").strip()
    if x == "":
        return None
    try:
        return float(x)
    except ValueError:
        return x


def _d(x, fmt="%d-%b-%Y"):
    x = (x or "").strip()
    if not x:
        return pd.NaT
    if x.count("-") == 1:
        x = f"{x}-{Y}"
    for f in (fmt, "%d-%b-%y", "%d-%m-%Y"):
        try:
            return pd.to_datetime(x, format=f)
        except ValueError:
            continue
    return pd.NaT


def gmp() -> pd.DataFrame:
    rows = []
    for ln in _GMP.strip().splitlines():
        p = (ln.split("|") + [""] * 17)[:17]
        price, g = _f(p[9]), _f(p[4])
        rows.append({
            "name": p[0], "category": p[1], "exchange": p[2] or ("BSE, NSE" if p[1] == "Mainboard" else None),
            "status": p[3], "gmp": g, "gmp_pct": (g / price * 100) if (g is not None and price) else None,
            "gmp_low": _f(p[5]), "gmp_high": _f(p[6]), "fire_rating": _f(p[7]), "sub_total": _f(p[8]),
            "price": price, "issue_size_cr": _f(p[10]), "lot": _f(p[11]),
            "open": _d(p[12]), "close": _d(p[13]), "allotment": _d(p[14]), "listing": _d(p[15]),
            "anchor": p[16] == "1", "updated": SNAPSHOT, "ig_url": None,
        })
    return pd.DataFrame(rows)


def subscription() -> pd.DataFrame:
    rows = []
    for ln in _SUB.strip().splitlines():
        p = ln.split("|")
        rows.append({
            "name": p[0], "category": p[1], "sub_total": _f(p[2]), "sub_as_of": p[3], "sub_qib": _f(p[4]),
            "sub_snii": _f(p[5]), "sub_bnii": _f(p[6]), "sub_nii": _f(p[7]), "sub_retail": _f(p[8]),
            "sub_employee": None, "pe": _f(p[9]), "close_date": _d(p[10]),
        })
    return pd.DataFrame(rows)


def performance() -> pd.DataFrame:
    rows = []
    for ln in _PERF.strip().splitlines():
        p = (ln.split("|") + [""] * 15)[:15]
        nse, bse = None, None
        for s in [s.strip() for s in p[2].split(",")]:
            if s.isdigit():
                bse = s
            elif s:
                nse = s
        rows.append({
            "name": p[0], "category": p[1], "nse_symbol": nse, "bse_code": bse,
            "listing_date": _d(p[3], "%d-%b-%y"), "issue_size_cr": _f(p[4]), "sub_total": _f(p[5]),
            "gmp": _f(p[6]), "price": _f(p[7]), "est_price": _f(p[8]), "listing_price": _f(p[9]),
            "listing_gain_pct": _f(p[10]), "listing_day_close": _f(p[11]), "listing_close_gain_pct": _f(p[12]),
            "ltp": _f(p[13]), "ltp_gain_pct": _f(p[14]), "ig_url": None,
        })
    df = pd.DataFrame(rows)
    df["gmp_pct"] = df["gmp"] / df["price"] * 100
    df["gmp_error_pct"] = df["listing_gain_pct"] - df["gmp_pct"]
    df["beat_gmp"] = df["listing_price"] >= df["est_price"]
    return df


# Day-wise GMP history example (Orient Cables, from its InvestorGain page)
def gmp_history(name: str) -> pd.DataFrame:
    if name != "Orient Cables":
        return pd.DataFrame(columns=["when", "gmp", "ts"])
    pts = [("22-Sep 12:02", 0), ("22-Sep 18:37", 34), ("23-Sep 11:37", 40), ("23-Sep 18:37", 45),
           ("24-Sep 12:37", 41), ("24-Sep 13:02", 50.5), ("24-Sep 13:37", 52), ("24-Sep 14:02", 50),
           ("24-Sep 15:02", 51.5), ("24-Sep 15:37", 58), ("24-Sep 16:37", 60), ("24-Sep 18:02", 68),
           ("24-Sep 21:02", 72), ("24-Sep 21:37", 105), ("24-Sep 22:02", 113), ("25-Sep 10:02", 113)]
    df = pd.DataFrame(pts, columns=["when", "gmp"])
    df["ts"] = pd.to_datetime(df["when"] + f"-{Y}", format="%d-%b %H:%M-%Y")
    return df


# Real brokerage calls reported by Business Standard on 25-Sep-2026 (for the offline demo)
def expert_news(name: str) -> pd.DataFrame:
    if name != "Orient Cables":
        return pd.DataFrame(columns=["title", "link", "source", "ts", "rating", "broker"])
    url = "https://www.business-standard.com/markets/ipo/orient-cables-ipo-brokerages-bullish-on-gains-from-india-s-digital-boom-126092500244_1.html"
    return pd.DataFrame([
        {"title": "Orient Cables IPO: Brokerages bullish on gains from India's digital boom", "link": url,
         "source": "Business Standard", "ts": pd.Timestamp(2026, 9, 25), "rating": "Apply", "broker": None},
        {"title": "Orient Cables (India) IPO opens today: Should you apply? Check price band, reviews, fresh GMP & more",
         "link": "https://www.businesstoday.in/markets/ipo-corner/story/orient-cables-india-ipo-opens-today-should-you-apply-check-price-band-reviews-fresh-gmp-more-557735-2026-09-25",
         "source": "Business Today", "ts": pd.Timestamp(2026, 9, 25), "rating": None, "broker": None},
    ])


def expert_views(name: str) -> pd.DataFrame:
    if name != "Orient Cables":
        return pd.DataFrame(columns=["ipo", "source", "rating", "note", "origin", "ts"])
    return pd.DataFrame([
        {"ipo": name, "source": "Bajaj Broking", "rating": "Apply", "note": "Top-4 networking-cable player, 22.9% share; data-centre & 5G tailwinds",
         "origin": "demo (Business Standard)", "ts": "2026-09-25"},
        {"ipo": name, "source": "SBI Securities", "rating": "Apply", "note": "Sticky customers; risks: raw-material volatility, customer concentration",
         "origin": "demo (Business Standard)", "ts": "2026-09-25"},
    ])
