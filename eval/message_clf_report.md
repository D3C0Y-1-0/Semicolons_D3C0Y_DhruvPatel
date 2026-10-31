# Message classifier: training report

Training rows: 7059 (1757 attacks). Model: char 2-5 + word 1-2 TF-IDF, calibrated logistic regression.

| Test set | n | AUROC | Avg precision | Precision | Recall | F1 | False-positive rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SMS Spam Collection (held-out 20%) | 1115 | 0.995 | 0.993 | 0.967 | 0.973 | 0.970 | 0.005 |
| Indian scams, unseen templates (5-fold by template) | 1487 | 0.906 | 0.944 | 0.886 | 0.874 | 0.880 | 0.239 |

Hardest unseen templates (share classified correctly): scam:gift_cards 0%, scam:otp_ceo 0%, scam:digital_arrest_hi 0%, scam:tech_support 0%, benign:bank_otp_notice 0%, benign:salary_credit 0%

Spot checks with the final model:

- 1.00: Hi Priya, Rajesh here (CFO). Urgent and confidential: transfer ₹45,00,000 to our new vendor account in 30 minutes.
- 0.98: Main CBI officer bol raha hoon. Video call pe raho, turant 2 lakh UPI karo.
- 0.00: Hi team, the quarterly review moves to Thursday 3 pm. Thanks, Rajesh
- 0.11: 482913 is your OTP for Rs 499 at Swiggy. Do not share this OTP with anyone. - HDFC Bank

Limits: the Indic set is synthetic and template-based, so real-world recall will be lower than the unseen-template score.
The classifier is one weighted signal (0.4) in the fusion engine, never the decision on its own.
