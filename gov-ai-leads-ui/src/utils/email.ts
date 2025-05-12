export const emailTemplate = `Subject: Unlock Your Agency's Potential with SoKat's Cutting-Edge AI Solutions

Dear [Recipient's Name],

As a leader in mission-critical decision-making, you understand the power of data in driving impactful outcomes. At SoKat, we specialize in translating the potential of AI into real-world solutions that accelerate mission success. Our team, comprised of Johns Hopkins University faculty and industry experts, is dedicated to creating AI tools that improve decision-making, reduce workloads, and enhance operational efficiency.

Why SoKat? Founded by Dr. Jim Kyung-Soo Liew, SoKat brings together the brightest minds in academia and industry to deliver end-to-end AI solutions that exceed client expectations. Our solutions have earned the trust of federal agencies and private organizations, making us a leader in AI-driven innovation.

Our Expertise Includes:

AI Solutions: Intelligent automation, machine learning, natural language processing, and predictive analytics to reduce workloads and drive measurable outcomes.

AI Education & Training: Custom AI training programs designed to equip your team with the knowledge to ethically adopt AI and drive long-term success.

Blockchain & Infrastructure: Secure and scalable solutions that modernize operations and ensure compliance in highly regulated environments.

Data Science: Transform your agency's data into actionable insights, empowering evidence-based decision-making and optimized programs.

Recent Recognition:

2023 GSA Applied AI Challenge: Winner for AI-based Solicitation Generating Tool

2022 VA Mission Daybreak: Phase 1 Award Winner for Intelligent Healthcare Assistant Application

2021 IRS Pilot Award: For Augmented Reality and AI-based Mobile Application

Let SoKat help you unlock the full potential of your data and drive meaningful change within your organization.

Ready to get started?
Contact us today to discuss how SoKat's tailored AI solutions can transform your agency's capabilities.

Best regards,
SoKat`;

export const sendEmail = (recipient: string, name: string) => {
  const emailContent = emailTemplate.replace('[Recipient\'s Name]', name);
  const mailtoLink = `mailto:${recipient}?subject=${encodeURIComponent('Unlock Your Agency\'s Potential with SoKat\'s Cutting-Edge AI Solutions')}&body=${encodeURIComponent(emailContent)}`;
  window.open(mailtoLink, '_blank');
};
