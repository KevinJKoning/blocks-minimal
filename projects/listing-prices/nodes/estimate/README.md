# What is a neighbourhood's typical price per square metre?

A neighbourhood's listings are a sample of its prices, and a few of them may still be wrong
after screening. The mean (`mean`) counts every listing equally, so one that remains too high
pulls it up. The median (`median`) depends only on where a listing falls among the others, so it
shrugs off what is left. What bears on it is how far the two differ from the truth under each
screen, and how the answer moves when the screen is loose.

On this data the median wins under every screen: about 2% typical error, against about 2.2% to
2.4% for the mean under the two screens, and about 30% for the mean with no screen at all, where a
single factor-of-10 listing moves a neighbourhood's mean by a large share. I would choose `median`: the question is a typical
price, and a median is what typical means when some listings may still be wrong.
