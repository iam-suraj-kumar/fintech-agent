import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("geolocation")


@mcp.tool()
async def geolocation(ip: str) -> dict:
    """Look up the real country, region, city, and ISP for a public IP address using ip-api.com."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"http://ip-api.com/json/{ip}")
            data = response.json()
    except httpx.HTTPError as exc:
        return {"country": "Unknown", "city": "Unknown", "error": str(exc)}

    if data.get("status") != "success":
        return {"country": "Unknown", "city": "Unknown", "error": data.get("message", "lookup failed")}

    return {
        "country": data.get("countryCode", "Unknown"),
        "city": data.get("city", "Unknown"),
        "region": data.get("regionName", "Unknown"),
        "isp": data.get("isp", "Unknown"),
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
