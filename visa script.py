from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time

# ==== CONFIG ====
CURRENT_DATE = datetime.strptime("2025-09-15", "%Y-%m-%d")  # Your current appointment
REFRESH_INTERVAL = 20  # seconds between scans

EMAIL_SENDER   = "junhong050707@gmail.com"
EMAIL_PASSWORD = "xwwg hrdp gcht frgl"      # Use app password
EMAIL_RECEIVER = "junhong050707@gmail.com"
# ===============

def send_email_alert(city, date_str):
    msg = MIMEMultipart()
    msg['From']    = EMAIL_SENDER
    msg['To']      = EMAIL_RECEIVER
    msg['Subject'] = "🛂 Earlier US Visa Slot Found!"
    body = f"A better appointment was found:\n\nCity: {city}\nDate: {date_str}\n\nRescheduling now…"
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(EMAIL_SENDER, EMAIL_PASSWORD)
            s.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        print("📧 Email alert sent.")
    except Exception as e:
        print("❌ Email failed:", e)

# ———— Attach to your running Chrome ————
options = Options()
options.add_experimental_option("debuggerAddress", "localhost:9222")
driver = webdriver.Chrome(options=options)
wait   = WebDriverWait(driver, 10)

def find_first_available_date(max_months=36):
    """Open calendar, scroll forward month by month, return first available date."""
    try:
        date_input = driver.find_element(By.ID, "appointments_consulate_appointment_date")
        driver.execute_script("arguments[0].click();", date_input)
        time.sleep(1)

        for _ in range(max_months):
            date_links = driver.find_elements(By.CSS_SELECTOR, "a.ui-state-default")

            if date_links:
                for link in date_links:
                    day_text = link.text.strip()
                    if not day_text:
                        continue

                    header = driver.find_element(By.CLASS_NAME, "ui-datepicker-title").text.strip()
                    full_date_str = f"{day_text} {header}"  # e.g. "24 April 2027"
                    full_date_obj = datetime.strptime(full_date_str, "%d %B %Y")

                    # Click the date
                    driver.execute_script("arguments[0].click();", link)
                    time.sleep(1)

                    # Close calendar to reset for next city
                    try:
                        driver.find_element(By.TAG_NAME, "body").click()
                        time.sleep(0.5)
                    except:
                        pass

                    return full_date_obj

            # No date in this month → go to next
            try:
                arrow_icon = driver.find_element(By.CLASS_NAME, "ui-icon-circle-triangle-e")
                next_btn = arrow_icon.find_element(By.XPATH, "./..")
                driver.execute_script("arguments[0].click();", next_btn)
                time.sleep(1)
            except Exception as e:
                print("⚠️ Could not scroll month:", e)
                break

        # After scanning all months, close the calendar
        try:
            driver.find_element(By.TAG_NAME, "body").click()
            time.sleep(0.5)
        except:
            pass

    except Exception as e:
        print("❌ Calendar error:", e)

    return None

# ———— Main Polling Loop ————
while True:
    print(f"[{time.strftime('%H:%M:%S')}] Scanning cities…")

    city_sel = Select(driver.find_element(By.ID, "appointments_consulate_appointment_facility_id"))
    for opt in city_sel.options:
        val, name = opt.get_attribute("value"), opt.text
        if not val:
            continue

        print(" →", name)
        city_sel.select_by_value(val)
        time.sleep(2)

        # Check for “System busy”
        try:
            busy = driver.find_element(By.ID, "consulate_date_time_not_available")
            if busy.is_displayed():
                print("   ⚠️ System busy — skip.")
                continue
        except:
            pass

        # Look for earliest available date
        found = find_first_available_date()
        if not found:
            print("   ❌ No dates found.")
            continue

        print("   ✅ Found:", found.date())

        if found >= CURRENT_DATE:
            print("   ⏩ Not earlier than current — skip.")
            continue

        # Earlier date found → Reschedule!
        try:
            # Pick any time
            td = Select(driver.find_element(By.ID, "appointments_consulate_appointment_time"))
            td.select_by_index(1)
            time.sleep(1)

            # Send alert
            send_email_alert(name, found.strftime("%Y-%m-%d"))

            # Click Reschedule
            btn = driver.find_element(By.ID, "appointments_submit")
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(2)

            # Confirm Yes
            yes = driver.find_element(By.CLASS_NAME, "button.alert")
            driver.execute_script("arguments[0].click();", yes)

            print("   🎉 Rescheduled to", found.date(), "at", name)
            exit()

        except Exception as e:
            print("   ❌ Reschedule error:", e)

    print(f"🔁 Waiting {REFRESH_INTERVAL}s before next round…\n")
    time.sleep(REFRESH_INTERVAL)

