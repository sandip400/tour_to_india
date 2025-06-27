import { GoogleGenerativeAI } from "@google/generative-ai";

const businessInfo = `
General Business Information:
Welcome to Priceless Memories, your trusted travel partner for discovering the vibrant culture, heritage, and natural wonders of India. At www.pricelessmemories.in, we offer expertly curated tour packages, local experiences, and destination guides to help you create meaningful and unforgettable journeys. In addition to travel planning, we also provide secure and convenient hotel, flight, train, and activity bookings across India.

Cancellation and Refund Policy:
We understand that plans may change. Bookings can be canceled up to 15 days prior to the travel date for a full refund, subject to individual service provider terms. Cancellations made within 15 days may attract cancellation charges. Refunds are processed to the original payment method within 7 working days.

Booking Services:
Through our platform, you can easily book domestic flights, train tickets, premium and budget hotels, guided tours, and adventure activities. All bookings are confirmed via email and accessible from your user dashboard. We ensure a smooth and secure booking experience with real-time availability and transparent pricing.

Customer Support:
For help with planning, bookings, or modifications, please contact our support team at support@pricelessmemories.in. We are happy to assist you with any questions related to your travel experience.

Head Office (Delhi):
Our main office is located at 2nd Floor, Connaught Place, New Delhi – 110001, India. You can reach us at +91 11 4567 8900 or email delhi@pricelessmemories.in.
Business hours are Monday to Friday from 9:00 AM to 6:00 PM, and Saturday from 10:00 AM to 4:00 PM. We are closed on Sundays.

Regional Office (Mumbai):
We also operate from our Mumbai office at 18th Floor, Bandra Kurla Complex, Mumbai – 400051, India. Contact us at +91 22 3344 5566 or email mumbai@pricelessmemories.in.
This office is open Monday to Friday from 10:00 AM to 7:00 PM and Saturday from 11:00 AM to 5:00 PM. Closed on Sundays.

FAQs:
What is your cancellation policy?
You can cancel your trip up to 15 days before the scheduled date for a full refund. Cancellations made later may involve charges, depending on the package and providers.

Do you offer international travel packages?
Currently, we specialize in Indian destinations. International packages may be introduced soon. Please check our website for updates.

How can I track my booking?
After booking, you will receive a confirmation email with your itinerary and reference number. You can track all your bookings through your dashboard.

Can I modify my tour after booking?
Yes, modifications are allowed up to 10 days before travel, subject to availability. Please contact support@pricelessmemories.in for changes.

Do you provide bookings as well?
Yes, we offer flight, train, hotel, and activity bookings across India. All services are available on our platform with instant confirmation.

What are your most popular destinations?
Top destinations include Kerala, Himachal Pradesh, Rajasthan, Goa, and the Northeast. We also offer special themed tours such as spiritual retreats, wildlife safaris, and cultural festivals.

Do you organize group or corporate tours?
Yes, we provide custom group tours and corporate travel packages. Reach out to us for tailored travel plans.

How do I contact your Delhi or Mumbai office?
For Delhi, call +91 11 4567 8900 or email delhi@pricelessmemories.in. For Mumbai, call +91 22 3344 5566 or email mumbai@pricelessmemories.in. We are here to help.

Tone Guidelines:
All responses are concise, polite, and formal. We avoid complex terms and maintain a consistent tone across all communication.
Example: “Thank you for reaching out! Please let us know if you need further assistance.”
`;

const API_KEY = "AIzaSyCc_BH0Hh9m3vzgVHvpKWHW6n6CKEyB87g"; // Replace with a valid Google Generative AI API key
const WEATHER_API_KEY = "2536b5706158eeb564146233e47f5f16"; // Replace with a valid OpenWeatherMap API key
const genAI = new GoogleGenerativeAI(API_KEY);
const model = genAI.getGenerativeModel({ model: "gemini-1.5-pro" });

let messages = {
    history: [],
};

async function sendMessage() {
    const fileInput = document.getElementById("fileInput");
    const userMessage = document.querySelector(".chat-window input").value.trim();
    let fileNames = "";
    let filesData = [];
    let unsupportedFiles = [];

    // Capture file names and process files
    if (fileInput.files.length > 0) {
        const files = Array.from(fileInput.files);
        fileNames = files.map(file => file.name).join(", ");
        [filesData, unsupportedFiles] = await processFiles(files);
        fileInput.value = ""; // Clear file input after processing
    }

    // Proceed only if there’s a message or files
    if (userMessage.length > 0 || filesData.length > 0) {
        try {
            document.querySelector(".chat-window input").value = "";
            const displayText = userMessage 
                ? userMessage + (fileNames ? " (with " + fileNames + ")" : "") 
                : (fileNames || "No content") + (unsupportedFiles.length > 0 ? ` (unsupported: ${unsupportedFiles.join(", ")})` : "");
            document.querySelector(".chat-window .chat").insertAdjacentHTML("beforeend", `
                <div class="user">
                    <p>${displayText}</p>
                </div>
            `);

            document.querySelector(".chat-window .chat").insertAdjacentHTML("beforeend", `
                <div class="loader"></div>
            `);

            const chat = model.startChat(messages);
            let messageToSend = [];
            if (userMessage.length > 0) {
                messageToSend.push({ text: userMessage });
                // Check for weather request
                if (userMessage.toLowerCase().includes("weather")) {
                    const cityMatch = userMessage.match(/weather in (\w+)/i);
                    if (cityMatch && cityMatch[1]) {
                        const weatherData = await getWeatherData(cityMatch[1]);
                        if (weatherData) {
                            messageToSend.push({ text: `Current weather data for ${cityMatch[1]}: ${weatherData}` });
                        }
                    }
                }
            }
            if (filesData.length > 0) {
                messageToSend = messageToSend.concat(filesData);
            }

            let result = await chat.sendMessageStream(messageToSend);

            document.querySelector(".chat-window .chat").insertAdjacentHTML("beforeend", `
                <div class="model">
                    <p></p>
                </div>
            `);

            let modelMessages = document.querySelectorAll(".chat-window .chat div.model");
            let fullResponse = '';
            for await (const chunk of result.stream) {
                const chunkText = chunk.text().replace(/\*\*/g, '').replace(/##/g, '');
                fullResponse += chunkText;
            }

            // Organize the response
            let formattedResponse = formatResponse(fullResponse);
            modelMessages[modelMessages.length - 1].querySelector("p").innerHTML = formattedResponse;

            // Scroll to the bottom of the chat
            const chatContainer = document.querySelector(".chat-window .chat");
            chatContainer.scrollTop = chatContainer.scrollHeight;

            messages.history.push({
                role: "user",
                parts: [{ text: displayText }],
            });

            messages.history.push({
                role: "model",
                parts: [{ text: modelMessages[modelMessages.length - 1].querySelector("p").innerHTML }],
            });

        } catch (error) {
            console.error("Error:", error);
            document.querySelector(".chat-window .chat").insertAdjacentHTML("beforeend", `
                <div class="error">
                    <p>Failed to send message. Please check your API keys or network connection. Error: ${error.message}</p>
                </div>
            `);
            // Scroll to the bottom of the chat in case of error
            const chatContainer = document.querySelector(".chat-window .chat");
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }

        document.querySelector(".chat-window .chat .loader").remove();
    } else if (unsupportedFiles.length > 0) {
        document.querySelector(".chat-window .chat").insertAdjacentHTML("beforeend", `
            <div class="error">
                <p>Warning: Only images can be uploaded. Unsupported files detected: ${unsupportedFiles.join(", ")}.</p>
            </div>
        `);
        document.querySelector(".chat-window .chat .loader")?.remove();
        // Scroll to the bottom of the chat for unsupported files
        const chatContainer = document.querySelector(".chat-window .chat");
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
}

// Function to format the response in an organized manner
function formatResponse(text) {
    let lines = text.split('\n').filter(line => line.trim().length > 0);

    if (lines.length === 0) return text;

    let formatted = '';
    let isList = false;
    let listType = 'ul'; // Default to unordered list

    for (let line of lines) {
        line = line.trim();
        if (line.match(/^\d+\.\s/)) {
            if (!isList || listType !== 'ol') {
                if (isList) formatted += '</ol>';
                formatted += '<ol>';
                isList = true;
                listType = 'ol';
            }
            formatted += `<li>${line.replace(/^\d+\.\s/, '')}</li>`;
        } else if (line.match(/^[-*]\s/)) {
            if (!isList || listType !== 'ul') {
                if (isList) formatted += '</ul>';
                formatted += '<ul>';
                isList = true;
                listType = 'ul';
            }
            formatted += `<li>${line.replace(/^[-*]\s/, '')}</li>`;
        } else {
            if (isList) {
                formatted += `</${listType}>`;
                isList = false;
            }
            formatted += `<p>${line}</p>`;
        }
    }

    if (isList) formatted += `</${listType}>`;

    return formatted;
}

async function processFiles(files) {
    const filePromises = [];
    const processedFiles = [];
    const unsupportedFiles = [];

    for (const file of files) {
        const reader = new FileReader();
        const promise = new Promise((resolve) => {
            reader.onload = async (e) => {
                const content = e.target.result;
                if (file.type.startsWith("image/")) {
                    processedFiles.push({
                        inlineData: {
                            data: content.split(",")[1], // Extract base64 data
                            mimeType: file.type
                        }
                    });
                    console.log(`Processed image: ${file.name}`);
                } else {
                    unsupportedFiles.push(file.name);
                    console.log(`Unsupported file: ${file.name}`);
                }
                resolve();
            };
            if (file.type.startsWith("image/")) {
                reader.readAsDataURL(file); // Read image as data URL
            } else {
                reader.onload(e => resolve()); // Resolve immediately for unsupported types
            }
        });
        filePromises.push(promise);
    }

    await Promise.all(filePromises); // Wait for all file reads to complete
    return [processedFiles, unsupportedFiles];
}

async function getWeatherData(city) {
    try {
        const response = await fetch(`https://api.openweathermap.org/data/2.5/weather?q=${city}&appid=${WEATHER_API_KEY}&units=metric`);
        const data = await response.json();
        if (data.cod === 200) {
            return `Temperature: ${data.main.temp}°C, Weather: ${data.weather[0].description}, Humidity: ${data.main.humidity}%, Wind Speed: ${data.wind.speed} m/s`;
        } else {
            return `Unable to fetch weather data for ${city}.`;
        }
    } catch (error) {
        console.error("Weather API error:", error);
        return `Error fetching weather data for ${city}.`;
    }
}

document.addEventListener("DOMContentLoaded", () => {
    document.querySelector(".chat-button")
        .addEventListener("click", () => {
            document.querySelector("body").classList.add("chat-open");
        });

    document.querySelector(".chat-window .input-area button")
        .addEventListener("click", () => sendMessage());

    document.getElementById("fileInput")
        .addEventListener("change", () => sendMessage());
});

document.querySelector(".chat-window button.close")
    .addEventListener("click", () => {
        document.querySelector("body").classList.remove("chat-open");
    });