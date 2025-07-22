def get_example_team_name_mappings():
    return example_mapped_team_names

def get_mls_team_mappings():
    return mls_team_mappings


example_mapped_team_names = {
    "Bayern Munich": ["Bayern", "Fußball-Club Bayern München e. V."],
    "Brighton": ["Brighton & Hove Albion"],
    "Bournemouth": ["AFC Bournemouth"],
    "Birmingham City": ["Birmingham"],
    "Blackburn Rovers": ["Blackburn"],
    "Bolton Wanderers": ["Bolton"],
    "Cardiff City": ["Cardiff"],
    "Derby County": ["Derby"],
    "Huddersfield Town": ["Huddersfield"],
    "Leeds United": ["Leeds"],
    "Leicester City": ["Leicester"],
    "Manchester City": ["Man City"],
    "Manchester United": ["Man Utd", "Man United"],
    "Newcastle United": ["Newcastle"],
    "Norwich City": ["Norwich"],
    "Nottingham Forest": ["Nott'm Forest", "Notts Forest"],
    "Queens Park Rangers": ["QPR"],
    "Tottenham Hotspur": ["Spurs", "Tottenham"],
    "Stoke City": ["Stoke"],
    "Wolverhampton Wanderers": ["Wolves", "Wolverhampton"],
}

# MLS team mappings for 2024-2025 season (30 teams)
mls_team_mappings = {
    # Eastern Conference
    "Atlanta United FC": ["Atlanta United", "ATL", "Atlanta", "ATLUTD"],
    "Charlotte FC": ["Charlotte", "CLT", "Charlotte Football Club"],
    "Chicago Fire FC": ["Chicago Fire", "CHI", "Chicago", "Fire FC"],
    "FC Cincinnati": ["Cincinnati", "CIN", "FC Cincy", "FCC"],
    "Columbus Crew": ["Columbus", "CLB", "Crew SC", "Columbus Crew SC"],
    "D.C. United": ["DC United", "DC", "DCU", "Washington"],
    "Inter Miami CF": ["Inter Miami", "MIA", "Miami", "IMCF"],
    "CF Montréal": ["Montreal", "MTL", "CF Montreal", "Impact"],
    "Nashville SC": ["Nashville", "NSH", "Nashville Soccer Club"],
    "New England Revolution": ["New England", "NE", "Revolution", "Revs"],
    "New York City FC": ["NYCFC", "NYC", "New York City", "NYC FC"],
    "New York Red Bulls": ["NY Red Bulls", "NYRB", "Red Bulls", "RBNY"],
    "Orlando City SC": ["Orlando City", "ORL", "Orlando", "OCSC"],
    "Philadelphia Union": ["Philadelphia", "PHI", "Union"],
    "Toronto FC": ["Toronto", "TOR", "TFC"],
    
    # Western Conference
    "Austin FC": ["Austin", "ATX", "Austin Football Club"],
    "Colorado Rapids": ["Colorado", "COL", "Rapids"],
    "FC Dallas": ["Dallas", "DAL", "FCD"],
    "Houston Dynamo FC": ["Houston Dynamo", "HOU", "Dynamo", "Houston"],
    "LA Galaxy": ["Galaxy", "LAG", "Los Angeles Galaxy"],
    "Los Angeles FC": ["LAFC", "Los Angeles FC"],
    "Minnesota United FC": ["Minnesota United", "MIN", "Minnesota", "MNUFC"],
    "Portland Timbers": ["Portland", "POR", "Timbers"],
    "Real Salt Lake": ["Salt Lake", "RSL", "Real SL"],
    "San Diego FC": ["San Diego", "SD", "SDFC"],  # New 2025 expansion team
    "San Jose Earthquakes": ["San Jose", "SJ", "Earthquakes", "Quakes"],
    "Seattle Sounders FC": ["Seattle Sounders", "SEA", "Sounders", "Seattle"],
    "Sporting Kansas City": ["Sporting KC", "SKC", "Kansas City", "Sporting"],
    "St. Louis City SC": ["St. Louis City", "STL", "St. Louis", "City SC"],
    "Vancouver Whitecaps FC": ["Vancouver", "VAN", "Whitecaps", "VWFC"],
}
