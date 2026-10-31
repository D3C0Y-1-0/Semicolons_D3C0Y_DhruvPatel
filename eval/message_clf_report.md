# Message classifier: training report

Training rows: 6438 (1313 attacks). Model: char 2-5 + word 1-2 TF-IDF, calibrated logistic regression.

| Test set | n | AUROC | Avg precision | Precision | Recall | F1 | False-positive rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SMS Spam Collection (held-out 20%) | 1115 | 0.995 | 0.992 | 0.986 | 0.966 | 0.976 | 0.002 |
| Indian scams, unseen templates (5-fold by template) | 866 | 0.849 | 0.900 | 0.883 | 0.802 | 0.841 | 0.200 |

Hardest unseen templates (share classified correctly): scam:gift_cards 0%, scam:otp_ceo 0%, scam:tech_support 0%, benign:bank_otp_notice 0%, benign:salary_credit 0%, benign:invoice_legit 0%

Spot checks with the final model:

- 1.00: Hi Priya, Rajesh here (CFO). Urgent and confidential: transfer ₹45,00,000 to our new vendor account in 30 minutes.
- 0.98: Main CBI officer bol raha hoon. Video call pe raho, turant 2 lakh UPI karo.
- 0.02: Hi team, the quarterly review moves to Thursday 3 pm. Thanks, Rajesh
- 0.10: 482913 is your OTP for Rs 499 at Swiggy. Do not share this OTP with anyone. - HDFC Bank

Limits: the Indic set is synthetic and template-based, so real-world recall will be lower than the unseen-template score.
The classifier is one weighted signal (0.4) in the fusion engine, never the decision on its own.
